import json
import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("behave.environment")


def _load_environment_variables(context):
    load_dotenv(dotenv_path=".env")
    context.base_url = os.getenv("BASE_URL")
    context.api_key = os.getenv("API_KEY")
    context.valid_nhs_number = os.getenv("VALID_NHS_NUMBER", "50000000004")
    context.aws_region = os.getenv("AWS_REGION", "eu-west-2")
    context.inserted_items = []
    context.abort_on_aws_error = os.getenv("ABORT_ON_AWS_FAILURE", "false").lower() == "true"
    context.keep_seed = os.getenv("KEEP_SEED", "false").lower() == "true"
    context.s3_bucket = os.getenv("S3_BUCKET_NAME")
    context.s3_upload_dir = os.getenv("S3_UPLOAD_DIR", "")
    context.s3_data_path = Path(os.getenv("S3_JSON_SOURCE_DIR", "./data/s3")).resolve()
    context.dynamodb_table_name = os.getenv("DYNAMODB_TABLE_NAME", "eligibilty_data_store")
    context.dynamo_data_path = Path(os.getenv("DYNAMO_JSON_SOURCE_DIR", "./data/out/dynamoDB")).resolve()
    logger.info("ABORT_ON_AWS_FAILURE=%s", context.abort_on_aws_error)
    logger.info("KEEP_SEED=%s", context.keep_seed)


def _connect_to_dynamodb(context):
    try:
        context.dynamodb = boto3.resource("dynamodb", region_name=context.aws_region)
        context.table = context.dynamodb.Table(context.dynamodb_table_name)
        _ = context.table.table_status
    except (boto3.exceptions.Boto3Error, BotoCoreError):
        logger.exception("DynamoDB not accessible")
        return False
    else:
        logger.info("Connected to DynamoDB table: %s", context.dynamodb_table_name)
        return True


def _get_dynamo_seed_files(context):
    if not context.dynamo_data_path.exists() or not context.dynamo_data_path.is_dir():
        logger.error("Seed directory not found: %s", context.dynamo_data_path)
        return []
    return list(context.dynamo_data_path.glob("*.json"))


def _load_seed_file(file_path: Path):
    try:
        with file_path.open() as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to load seed file: %s", file_path)
        return []


def _insert_dynamodb_items(context, items):
    for item in items:
        try:
            context.table.put_item(Item=item)
            context.inserted_items.append(item)
        except (boto3.exceptions.Boto3Error, BotoCoreError):
            logger.exception("Failed to insert item %s", item.get("PK", "<unknown>"))


def _setup_dynamodb(context):
    if not _connect_to_dynamodb(context):
        if context.abort_on_aws_error:
            context.abort_all = True
        return False
    json_files = _get_dynamo_seed_files(context)
    if not json_files:
        logger.error("No JSON files found in the directory: %s", context.dynamo_data_path)
        if context.abort_on_aws_error:
            context.abort_all = True
        return False
    logger.info("Found %d JSON files to insert into DynamoDB", len(json_files))
    for file_path in json_files:
        items = _load_seed_file(file_path)
        if not items:
            if context.abort_on_aws_error:
                context.abort_all = True
            continue
        logger.info("Inserting %d items from %s...", len(items), file_path.name)
        _insert_dynamodb_items(context, items)
    logger.info("Inserted %d items from %d files", len(context.inserted_items), len(json_files))
    return True


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
        upload_success = True
        for file_path in json_files:
            key = f"{context.s3_upload_dir}/{file_path.name}" if context.s3_upload_dir else file_path.name
            try:
                s3_client.upload_file(str(file_path), context.s3_bucket, key)
                logger.info("Uploaded %s to s3://%s/%s", file_path.name, context.s3_bucket, key)
            except (boto3.exceptions.Boto3Error, BotoCoreError):
                logger.exception("Failed to upload %s", file_path.name)
                upload_success = False
    except (boto3.exceptions.Boto3Error, BotoCoreError):
        logger.exception("S3 upload setup failed")
        if context.abort_on_aws_error:
            context.abort_all = True
        return False
    else:
        return upload_success


def before_all(context):
    logger.info("Loading .env and initializing AWS fixtures...")
    _load_environment_variables(context)
    _setup_dynamodb(context)
    _setup_s3(context)


def before_scenario(context, scenario):
    if getattr(context, "abort_all", False):
        scenario.skip("Skipping scenario due to setup failure")
    if "requires_dynamodb" in scenario.tags and not context.inserted_items:
        scenario.skip("Skipping due to missing seeded DynamoDB data")


def _cleanup_dynamodb(context):
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
            except (boto3.exceptions.Boto3Error, BotoCoreError):
                logger.exception("Failed to delete item (%s, %s)", nhs_number, attribute_type)
        else:
            logger.error("Cannot delete item — missing NHS_NUMBER or ATTRIBUTE_TYPE: %s", item)
    logger.info("Deleted %d/%d DynamoDB items", delete_count, len(context.inserted_items))


def _cleanup_s3(context):
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
            except (boto3.exceptions.Boto3Error, BotoCoreError):
                logger.exception("Failed to delete s3://%s/%s", context.s3_bucket, key)
        logger.info("Deleted %d/%d files from S3", deleted_files, len(json_files))
    except (boto3.exceptions.Boto3Error, BotoCoreError):
        logger.exception("S3 cleanup failed")


def after_all(context):
    if getattr(context, "keep_seed", False):
        logger.info("KEEP_SEED=true — skipping cleanup.")
        return
    _cleanup_dynamodb(context)
    _cleanup_s3(context)
