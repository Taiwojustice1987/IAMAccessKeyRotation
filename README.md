# IAMAccessKeyRotation

**Automated AWS IAM Access Key Rotation with Reporting and Notifications**

## Overview

IAMAccessKeyRotation is an AWS Lambda function that automates the rotation of IAM access keys across multiple AWS accounts. It improves security by ensuring that keys are regularly rotated, old keys are deactivated, and administrators are notified of changes. The function also generates a detailed CSV report uploaded to an S3 bucket for auditing purposes.

## Features

- Automatically rotates IAM access keys older than a configurable threshold.
- Deactivates and deletes old keys securely.
- Supports multiple AWS accounts via IAM roles.
- Generates detailed rotation reports in CSV format stored in an S3 bucket.
- Sends SNS notifications upon completion.
- Scheduled execution using AWS EventBridge (CloudWatch Events).

## Configuration

### Environment Variables
Set the following in the Lambda environment variables or directly in the script:

- `SNS_TOPIC_ARN` - ARN of the SNS topic to send notifications.
- `THRESHOLD_DAYS` - Number of days after which keys should be rotated (e.g., `2`).

### Configurable Variables in the Script
- `ACCOUNT_ROLES` - List of IAM roles to assume in target accounts.
- `BUCKET_NAME` - S3 bucket to store the CSV report.
- `ROTATION_DAYS` - Number of days after which keys are rotated.

## Deployment

1. Package the Lambda function:

```bash
zip function.zip lambda_function.py
