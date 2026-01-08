import boto3
import secrets
import string
import os

SECRET_NAME = os.environ.get('SECRET_NAME')
REGION_NAME = os.environ.get('AWS_REGION')

def generate_password(length=32):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for i in range(length))

def lambda_handler(event, context):
    sm_client = boto3.client('secretsmanager', region_name=REGION_NAME)

    new_password = generate_password()

    try:
        resp = sm_client.put_secret_value(
            SecretId=SECRET_NAME,
            SecretString=new_password,
            VersionStages=['AWSPENDING']
        )

        print(f"Successfully created pending version for {SECRET_NAME}")
        return {
            "status": "success",
            "secret_name": SECRET_NAME,
            "version_id": resp['VersionId']
        }

    except sm_client.exceptions.ResourceNotFoundException:
        raise Exception(f"The secret '{SECRET_NAME}' was not found in region '{REGION_NAME}'.")
    except Exception as e:
        raise Exception(f"Error creating pending secret: {str(e)}")
