import json
import logging
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("behave.environment")


def _load_environment_variables(context):
    """Load environment variables and set up context."""
    load_dotenv(dotenv_path=".env")

    # API configuration
    context.base_url = os.getenv("BASE_URL")
    context.api_key = os.getenv("API_KEY")
    context.valid_nhs_number = os.getenv("VALID_NHS_NUMBER", "50000000004")

    # AWS configuration
    context.aws_region = os.getenv("AWS_REGION", "eu-west-2")
    context.inserted_items = []
    context.abort_on_aws_error = os.getenv("ABORT_ON_AWS_FAILURE", "false").lower() == "true"
    context.keep_seed = os.getenv("KEEP_SEED", "false").lower() == "true"

    # S3 configuration
    context.s3_bucket = os.getenv("S3_BUCKET_NAME")
    context.s3_upload_dir = os.getenv("S3_UPLOAD_DIR", "")
    context.s3_data_path = Path(os.getenv("S3_JSON_SOURCE_DIR", "./data/s3")).resolve()

    # DynamoDB configuration
    context.dynamodb_table_name = os.getenv("DYNAMODB_TABLE_NAME", "eligibilty_data_store")
    context.dynamo_data_path = Path(os.getenv("DYNAMO_JSON_SOURCE_DIR", "./data/dynamoDB/test_data.json")).resolve()

    logger.info("ABORT_ON_AWS_FAILURE=%s", context.abort_on_aws_error)
    logger.info("KEEP_SEED=%s", context.keep_seed)


def _setup_dynamodb(context):
    """Set up DynamoDB connection and seed data."""
    try:
        context.dynamodb = boto3.resource("dynamodb", region_name=context.aws_region)
        context.table = context.dynamodb.Table(context.dynamodb_table_name)
        _ = context.table.table_status
        logger.info("Connected to DynamoDB table: %s", context.dynamodb_table_name)
    except (boto3.exceptions.Boto3Error, boto3.exceptions.BotoCoreError):
        logger.exception("DynamoDB not accessible")
        if context.abort_on_aws_error:
            context.abort_all = True
        return False

    if not context.dynamo_data_path.exists():
        logger.error("Seed file not found: %s", context.dynamo_data_path)
        if context.abort_on_aws_error:
            context.abort_all = True
        return False

    try:
        with context.dynamo_data_path.open() as f:
            items = json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load seed file")
        if context.abort_on_aws_error:
            context.abort_all = True
        return False

    logger.info("Inserting %d items into DynamoDB...", len(items))
    for item in items:
        try:
            context.table.put_item(Item=item)
            context.inserted_items.append(item)
        except (boto3.exceptions.Boto3Error, boto3.exceptions.BotoCoreError):
            logger.exception("Failed to insert item %s", item.get("PK", "<unknown>"))

    logger.info("Inserted %d items", len(context.inserted_items))
    return True


def _setup_s3(context):
    """Upload test data to S3 bucket."""
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
        upload_success = True
        for file_path in json_files:
            key = f"{context.s3_upload_dir}/{file_path.name}" if context.s3_upload_dir else file_path.name
            try:
                s3_client.upload_file(str(file_path), context.s3_bucket, key)
                logger.info("Uploaded %s to s3://%s/%s", file_path.name, context.s3_bucket, key)
            except (boto3.exceptions.Boto3Error, boto3.exceptions.BotoCoreError):
                logger.exception("Failed to upload %s", file_path.name)
                upload_success = False

        if upload_success:
            return True
    except (boto3.exceptions.Boto3Error, boto3.exceptions.BotoCoreError):
        logger.exception("S3 upload setup failed")
        if context.abort_on_aws_error:
            context.abort_all = True
        return False


def before_all(context):
    """Initialize test environment before all tests."""
    logger.info("Loading .env and initializing AWS fixtures...")

    # Load environment variables
    _load_environment_variables(context)

    # Set up DynamoDB
    _setup_dynamodb(context)

    # Set up S3
    _setup_s3(context)


def before_scenario(context, scenario):
    if getattr(context, "abort_all", False):
        scenario.skip("Skipping scenario due to setup failure")

    if "requires_dynamodb" in scenario.tags and not context.inserted_items:
        scenario.skip("Skipping due to missing seeded DynamoDB data")


def _cleanup_dynamodb(context):
    """Clean up seeded items from DynamoDB."""
    if not context.inserted_items:
        logger.info("No items were inserted — skipping DynamoDB cleanup.")
        return

    logger.info("Cleaning up seeded items from DynamoDB...")
    delete_count = 0
    for item in context.inserted_items:
        nhs_number = item.get("NHS_NUMBER")
        attribute_type = item.get("ATTRIBUTE_TYPE")

        if nhs_number and attribute_type:
            try:
                context.table.delete_item(Key={"NHS_NUMBER": nhs_number, "ATTRIBUTE_TYPE": attribute_type})
                delete_count += 1
            except (boto3.exceptions.Boto3Error, boto3.exceptions.BotoCoreError):
                logger.exception("Failed to delete item (%s, %s)", nhs_number, attribute_type)
        else:
            logger.error("Cannot delete item — missing NHS_NUMBER or ATTRIBUTE_TYPE: %s", item)

    logger.info("Deleted %d/%d DynamoDB items", delete_count, len(context.inserted_items))


def _cleanup_s3(context):
    """Clean up uploaded files from S3."""
    if not (context.s3_bucket and context.s3_data_path.exists()):
        logger.info("Skipping S3 cleanup — no bucket or source directory not found.")
        return

    logger.info("Cleaning up uploaded files from S3...")
    try:
        s3_client = boto3.client("s3", region_name=context.aws_region)
        json_files = list(context.s3_data_path.glob("*.json"))
        deleted_files = 0

        for file_path in json_files:
            key = f"{context.s3_upload_dir}/{file_path.name}" if context.s3_upload_dir else file_path.name
            try:
                s3_client.delete_object(Bucket=context.s3_bucket, Key=key)
                logger.info("Deleted s3://%s/%s", context.s3_bucket, key)
                deleted_files += 1
            except (boto3.exceptions.Boto3Error, boto3.exceptions.BotoCoreError):
                logger.exception("Failed to delete s3://%s/%s", context.s3_bucket, key)

        logger.info("Deleted %d/%d files from S3", deleted_files, len(json_files))
    except (boto3.exceptions.Boto3Error, boto3.exceptions.BotoCoreError):
        logger.exception("S3 cleanup failed")


def after_all(context):
    """Clean up resources after all tests have run."""
    # Early exit if KEEP_SEED is true
    if getattr(context, "keep_seed", False):
        logger.info("KEEP_SEED=true — skipping cleanup.")
        return

    # Clean up DynamoDB
    _cleanup_dynamodb(context)

    # Clean up S3
    _cleanup_s3(context)
