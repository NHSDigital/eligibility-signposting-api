import json
import logging
import os
import secrets
import string

import boto3
from mangum.types import LambdaContext, LambdaEvent

SECRET_NAME = os.environ.get("SECRET_NAME")
REGION_NAME = os.environ.get("AWS_REGION")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class PendingVersionExistsError(Exception):
    pass


def generate_password(length: int = 32) -> str:
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def lambda_handler(
    event: LambdaEvent,  # noqa: ARG001
    context: LambdaContext,
) -> dict:
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

                raise PendingVersionExistsError(msg)
    except sm_client.exceptions.ResourceNotFoundException:
        logger.info("Secret not found. Proceeding to create (assuming it will be initialized).")

    new_password = generate_password()

    try:
        resp = sm_client.put_secret_value(SecretId=SECRET_NAME, SecretString=new_password, VersionStages=["AWSPENDING"])

        logger.info(
            json.dumps({"event": "pending_version_created", "version_id": resp["VersionId"], "status": "success"})
        )
        return {"status": "success", "secret_name": SECRET_NAME, "version_id": resp["VersionId"]}

    except sm_client.exceptions.ResourceNotFoundException as e:
        exception_message = f"The secret '{SECRET_NAME}' was not found in region '{REGION_NAME}'."
        raise sm_client.exceptions.ResourceNotFoundException(exception_message) from e
    except Exception as e:
        logger.exception(json.dumps({"event": "rotation_failed", "type": type(e).__name__}))
        raise
