import logging
import boto3
import csv
import io
from datetime import datetime, timezone

# ========== CONFIGURABLE VARIABLES ==========
ACCOUNT_ROLES = [
    "arn:aws:iam::135808961729:role/IAMKeyRotationRole"
]

BUCKET_NAME = "my-key-rotation-reports-central"
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:626635400294:IAMKeyRotationNotifications"
ROTATION_DAYS = 2
# ===========================================

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("Lambda module loaded")

def lambda_handler(event, context):
    logger.info("Lambda execution started")
    s3 = boto3.client('s3')
    sns = boto3.client('sns')
    rotated_keys = []
    now = datetime.now(timezone.utc)

    for role_arn in ACCOUNT_ROLES:
        sts = boto3.client('sts')

        try:
            # Assume the IAMKeyRotationRole in target account
            creds = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName='RotateKeysSession'
            )['Credentials']

            iam = boto3.client(
                'iam',
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken']
            )

            users = iam.list_users()['Users']
            logger.info(f"Found {len(users)} users in account {role_arn}")

            for user in users:
                username = user['UserName']
                keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']
                logger.info(f"User {username} has {len(keys)} keys")

                for key in keys:
                    age_days = (now - key['CreateDate']).days
                    logger.info(f"Key {key['AccessKeyId']} for user {username} is {age_days} days old")

                    if age_days > ROTATION_DAYS:
                        logger.info(f"Rotating key {key['AccessKeyId']} for user {username}")

                        if len(keys) >= 2:
                            oldest_key = sorted(keys, key=lambda k: k['CreateDate'])[0]
                            iam.delete_access_key(UserName=username, AccessKeyId=oldest_key['AccessKeyId'])
                            logger.info(f"Deleted oldest key {oldest_key['AccessKeyId']} for user {username}")

                        new_key = iam.create_access_key(UserName=username)['AccessKey']
                        iam.update_access_key(UserName=username, AccessKeyId=key['AccessKeyId'], Status='Inactive')
                        iam.delete_access_key(UserName=username, AccessKeyId=key['AccessKeyId'])

                        rotated_keys.append({
                            "AccountRole": role_arn,
                            "User": username,
                            "OldKey": key['AccessKeyId'],
                            "NewKey": new_key['AccessKeyId'],
                            "AgeDays": age_days
                        })
                        logger.info(f"Created new key {new_key['AccessKeyId']} and disabled old key {key['AccessKeyId']} for {username}")

        except Exception as e:
            logger.error(f"Error processing {role_arn}: {e}")

    # Upload report if any keys rotated
    if rotated_keys:
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["AccountRole", "User", "OldKey", "NewKey", "AgeDays"])
        writer.writeheader()
        writer.writerows(rotated_keys)

        report_name = f"rotated_keys_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        s3.put_object(Bucket=BUCKET_NAME, Key=report_name, Body=csv_buffer.getvalue())
        logger.info(f"Report uploaded to S3: {BUCKET_NAME}/{report_name}")

        message = (
            f"IAM access key rotation completed.\n\n"
            f"Report saved in S3 bucket: {BUCKET_NAME}/{report_name}\n"
            f"Total keys rotated: {len(rotated_keys)}"
        )
        try:
            sns.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject="IAM Access Key Rotation Summary")
            logger.info(f"SNS notification sent to {SNS_TOPIC_ARN}")
        except Exception as e:
            logger.error(f"Error sending SNS notification: {e}")
    else:
        logger.info("No keys required rotation during this run.")

    logger.info("Lambda execution finished")
    return {
        "status": "done",
        "rotated_count": len(rotated_keys),
        "report": rotated_keys[0]['NewKey'] if rotated_keys else None
    }
