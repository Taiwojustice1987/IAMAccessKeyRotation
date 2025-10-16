
import boto3
from datetime import datetime, timezone, timedelta
import os

def lambda_handler(event, context):
    iam = boto3.client('iam')
    sns = boto3.client('sns')
    topic_arn = os.environ.get('SNS_TOPIC_ARN')

    users = iam.list_users()['Users']
    threshold_days = int(os.environ.get('THRESHOLD_DAYS', 2))
    now = datetime.now(timezone.utc)

    for user in users:
        username = user['UserName']
        keys = iam.list_access_keys(UserName=username)['AccessKeyMetadata']

        for key in keys:
            key_id = key['AccessKeyId']
            create_date = key['CreateDate']
            age_days = (now - create_date).days

            if age_days > threshold_days:
                # Deactivate old key
                iam.update_access_key(UserName=username, AccessKeyId=key_id, Status='Inactive')

                # Create new access key
                new_key = iam.create_access_key(UserName=username)['AccessKey']

                message = (
                    f"IAM Access Key rotated for user: {username}\n"
                    f"Old Key: {key_id} (now inactive)\n"
                    f"New Key: {new_key['AccessKeyId']}\n"
                    f"Created on: {new_key['CreateDate']}"
                )

                print(message)

                # Send SNS notification
                if topic_arn:
                    sns.publish(
                        TopicArn=topic_arn,
                        Subject="IAM Access Key Rotated Automatically",
                        Message=message
                    )

    return {"status": "Key rotation completed"}
