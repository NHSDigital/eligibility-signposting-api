import json
import logging
import os
import secrets
import string

import boto3

SECRET_NAME = os.environ.get("SECRET_NAME")
REGION_NAME = os.environ.get("AWS_REGION")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def generate_password(length=32):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for i in range(length))


def lambda_handler(event, context):
    sm_client = boto3.client("secretsmanager", region_name=REGION_NAME)

    logger.info(
        json.dumps(
            {
                "event": "rotation_started",
                "request_id": context.aws_request_id,
                "secret_name": SECRET_NAME,
                "function": "create_pending_secret",
            }
        )
    )

    try:
        metadata = sm_client.describe_secret(SecretId=SECRET_NAME)
        # Check if any version currently has the 'AWSPENDING' label
        for version_id, stages in metadata.get("VersionIdsToStages", {}).items():
            if "AWSPENDING" in stages:
                msg = f"Pending version already exists with version_id: {version_id}."

                logger.warning(
                    json.dumps(
                        {
                            "event": "rotation_aborted",
                            "reason": "pending_version_exists",
                            "pending_version_id": version_id,
                        }
                    )
                )

                raise Exception(msg)
    except sm_client.exceptions.ResourceNotFoundException:
        logger.info("Secret not found. Proceeding to create (assuming it will be initialized).")

    new_password = generate_password()

    try:
        resp = sm_client.put_secret_value(SecretId=SECRET_NAME, SecretString=new_password, VersionStages=["AWSPENDING"])

        logger.info(
            json.dumps({"event": "pending_version_created", "version_id": resp["VersionId"], "status": "success"})
        )
        return {"status": "success", "secret_name": SECRET_NAME, "version_id": resp["VersionId"]}

    except sm_client.exceptions.ResourceNotFoundException:
        raise Exception(f"The secret '{SECRET_NAME}' was not found in region '{REGION_NAME}'.")
    except Exception as e:
        logger.error(json.dumps({"event": "rotation_failed", "error": str(e), "type": type(e).__name__}))
        raise Exception(f"Error creating pending secret: {e!s}")
