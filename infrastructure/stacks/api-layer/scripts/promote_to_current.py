import boto3
import os

SECRET_NAME = os.environ.get('SECRET_NAME')
REGION_NAME = os.environ.get('AWS_REGION')

def lambda_handler(event, context):
    sm_client = boto3.client('secretsmanager', region_name=REGION_NAME)
    print(f"Starting promotion for secret: {SECRET_NAME}")

    try:
        metadata = sm_client.describe_secret(SecretId=SECRET_NAME)
        pending_version = None
        current_version_id = None

        for version_id, stages in metadata['VersionIdsToStages'].items():
            if 'AWSPENDING' in stages:
                pending_version = version_id
            if 'AWSCURRENT' in stages:
                current_version_id = version_id

        if not pending_version:
            print("No version with label 'AWSPENDING' found. Nothing to do.")
            return {"status": "skipped", "reason": "no_pending_version"}

        if pending_version != current_version_id:
            print(f"Promoting {pending_version} to AWSCURRENT...")
            update_kwargs = {
                'SecretId': SECRET_NAME,
                'VersionStage': 'AWSCURRENT',
                'MoveToVersionId': pending_version
            }
            if current_version_id:
                update_kwargs['RemoveFromVersionId'] = current_version_id

            sm_client.update_secret_version_stage(**update_kwargs)

        sm_client.update_secret_version_stage(
            SecretId=SECRET_NAME,
            VersionStage='AWSPENDING',
            RemoveFromVersionId=pending_version
        )

        return {
            'status': 'success',
            'action': 'promoted_and_cleaned',
            'new_current_version': pending_version
        }

    except Exception as e:
        print(f"Error promoting secret: {str(e)}")
        raise e
