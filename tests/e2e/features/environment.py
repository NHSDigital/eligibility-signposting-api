import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("behave.environment")


def _load_environment_variables(context):
    try:
        load_dotenv(dotenv_path=".env")
        logger.info("Loaded environment variables from .env file")
    except OSError as e:
        logger.warning("Failed to load .env file: %s", e)

    context.base_url = os.getenv("BASE_URL", "http://localhost:8000")
    context.api_key = os.getenv("API_KEY", "test-api-key")
    context.valid_nhs_number = os.getenv("VALID_NHS_NUMBER", "50000000004")
    context.aws_region = os.getenv("AWS_REGION", "eu-west-2")
    context.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    context.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    context.aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    context.abort_on_aws_error = (
        os.getenv("ABORT_ON_AWS_FAILURE", "false").lower() == "true"
    )
    context.keep_seed = os.getenv("KEEP_SEED", "false").lower() == "true"
    context.dynamodb_table_name = os.getenv(
        "DYNAMODB_TABLE_NAME", "eligibilty_data_store"
    )
    context.s3_bucket = os.getenv("S3_BUCKET_NAME")
    context.s3_upload_dir = os.getenv("S3_UPLOAD_DIR", "")
    context.s3_data_path = Path(os.getenv("S3_JSON_SOURCE_DIR", "./data/s3")).resolve()
    context.api_gateway_url = os.getenv(
        "API_GATEWAY_URL", "https://test.eligibility-signposting-api.nhs.uk"
    )

    logger.info("ABORT_ON_AWS_FAILURE=%s", context.abort_on_aws_error)
    logger.info("KEEP_SEED=%s", context.keep_seed)
    logger.info("BASE_URL: %s", context.base_url)
    logger.info("AWS_REGION: %s", context.aws_region)
    logger.info("DYNAMODB_TABLE: %s", context.dynamodb_table_name)
    logger.info("S3_BUCKET: %s", context.s3_bucket)


def _setup_s3(context):
    if not context.s3_bucket:
        logger.info("Skipping S3 upload — no S3_BUCKET_NAME set.")
        return True

    logger.info(
        "Uploading JSON files from %s to S3 bucket: %s/%s",
        context.s3_data_path,
        context.s3_bucket,
        context.s3_upload_dir,
    )
    try:
        s3_client = boto3.client("s3", region_name=context.aws_region)
        if not context.s3_data_path.exists():
            logger.error("S3 source directory not found: %s", context.s3_data_path)
            return False

        json_files = list(context.s3_data_path.glob("*.json"))
        for file_path in json_files:
            key = (
                f"{context.s3_upload_dir}/{file_path.name}"
                if context.s3_upload_dir
                else file_path.name
            )
            try:
                s3_client.upload_file(str(file_path), context.s3_bucket, key)
                logger.info(
                    "Uploaded %s to s3://%s/%s", file_path.name, context.s3_bucket, key
                )
            except (Exception, BotoCoreError):
                logger.exception("Failed to upload %s", file_path.name)
    except (Exception, BotoCoreError):
        logger.exception("S3 upload setup failed")
        if context.abort_on_aws_error:
            context.abort_all = True
        return False
    return True


def before_all(context):
    logger.info("Loading .env and initializing AWS fixtures...")
    _load_environment_variables(context)

    context.aws_available = True
    try:
        logger.info("Setting up S3 (optional)...")
        _setup_s3(context)
    except OSError as e:
        logger.warning("AWS setup failed: %s", e)
        context.aws_available = False


def before_scenario(context, scenario):
    if getattr(context, "abort_all", False):
        logger.warning("Skipping scenario '%s' due to setup failure", scenario.name)
        scenario.skip("Skipping scenario due to setup failure")
        return

    logger.info("Running scenario: %s", scenario.name)


def before_feature(context, feature):
    """Initialize feature-level context for data setup tracking."""
    context.feature_data_setup_done = False
    context.feature_dynamodb_items_count = 0
    context.feature_uploader = None
    logger.info("Initialized feature context for: %s", feature.name)


def after_feature(context, feature):
    """Cleanup feature-level DynamoDB data."""
    if getattr(context, "keep_seed", False):
        logger.info(
            "KEEP_SEED=true — skipping feature-level DynamoDB cleanup for: %s",
            feature.name,
        )
        return

    if hasattr(context, "feature_uploader") and context.feature_uploader:
        if context.feature_dynamodb_items_count > 0:
            logger.info(
                "Cleaning up %d DynamoDB items for feature: %s",
                context.feature_dynamodb_items_count,
                feature.name,
            )
            try:
                # Use the uploader's cleanup method if available
                if hasattr(context.feature_uploader, "delete_data"):
                    context.feature_uploader.delete_data()
                    logger.info(
                        "Successfully cleaned up DynamoDB data for feature: %s",
                        feature.name,
                    )
            except Exception:
                logger.exception(
                    "Failed to cleanup DynamoDB data for feature: %s", feature.name
                )


def after_all(context):
    if context.keep_seed:
        logger.info("KEEP_SEED=true — skipping cleanup.")
        return

    # Cleanup S3 if necessary (optional)
    if context.s3_bucket and context.s3_data_path.exists():
        logger.info("Cleaning up uploaded files from S3...")
        try:
            s3_client = boto3.client("s3", region_name=context.aws_region)
            json_files = list(context.s3_data_path.glob("*.json"))
            for file_path in json_files:
                key = (
                    f"{context.s3_upload_dir}/{file_path.name}"
                    if context.s3_upload_dir
                    else file_path.name
                )
                try:
                    s3_client.delete_object(Bucket=context.s3_bucket, Key=key)
                    logger.info("Deleted s3://%s/%s", context.s3_bucket, key)
                except (Exception, BotoCoreError):
                    logger.exception(
                        "Failed to delete s3://%s/%s", context.s3_bucket, key
                    )
        except Exception:
            logger.exception("S3 cleanup failed")
