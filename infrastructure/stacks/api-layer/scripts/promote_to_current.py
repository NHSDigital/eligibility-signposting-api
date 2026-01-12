import json
import logging
import os

import boto3

SECRET_NAME = os.environ.get("SECRET_NAME")
REGION_NAME = os.environ.get("AWS_REGION")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(
    event: dict,  # noqa: ARG001
    context: object,
) -> dict:
    sm_client = boto3.client("secretsmanager", region_name=REGION_NAME)
    logger.info(
        json.dumps(
            {
                "event": "promotion_started",
                "request_id": context.aws_request_id,
                "secret_name": SECRET_NAME,
                "function": "promote_to_current",
            }
        )
    )

    try:
        metadata = sm_client.describe_secret(SecretId=SECRET_NAME)
        pending_version = None
        current_version = None
        for version_id, stages in metadata["VersionIdsToStages"].items():
            if "AWSPENDING" in stages:
                pending_version = version_id
            if "AWSCURRENT" in stages:
                current_version = version_id

        if pending_version:
            logger.info(
                json.dumps(
                    {
                        "event": "promoting_version",
                        "pending_version_id": pending_version,
                        "old_current_version_id": current_version,
                        "action": "swap_AWSCURRENT",
                    }
                )
            )

            swap_kwargs = {"SecretId": SECRET_NAME, "VersionStage": "AWSCURRENT", "MoveToVersionId": pending_version}

            if current_version:
                swap_kwargs["RemoveFromVersionId"] = current_version

            sm_client.update_secret_version_stage(**swap_kwargs)

            sm_client.update_secret_version_stage(
                SecretId=SECRET_NAME, VersionStage="AWSPENDING", RemoveFromVersionId=pending_version
            )

            logger.info(
                json.dumps({"event": "promotion_complete", "new_current_version": pending_version, "status": "success"})
            )

            return {"status": "success", "action": "promoted_and_cleaned", "new_current_version": pending_version}

    except Exception as e:
        logger.exception(json.dumps({"event": "promotion_failed", "type": type(e).__name__}))
        raise

    else:
        logger.warning(
            json.dumps({"event": "promotion_skipped", "reason": "no_pending_version_found", "secret_name": SECRET_NAME})
        )
        return {"status": "skipped", "reason": "no_pending_version"}
