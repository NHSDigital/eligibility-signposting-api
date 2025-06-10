import json
import logging
import os
from pathlib import Path

import boto3
import pytest
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv(dotenv_path=".env.local")

# Constants
BASE_URL = os.getenv("BASE_URL", "https://sandbox.api.service.nhs.uk/eligibility-signposting-api")
API_KEY = os.getenv("API_KEY", "")
VALID_NHS_NUMBER = os.getenv("VALID_NHS_NUMBER", "50000000004")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "eligibility_data_store")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")

# Resolve test data path robustly
BASE_DIR = Path(__file__).resolve().parent.parent
DYNAMO_DATA_PATH = BASE_DIR / "data" / "dynamoDB" / "test_data.json"

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption("--keep-seed", action="store_true", default=False, help="Keep DynamoDB seed data after tests")


@pytest.fixture(scope="session", autouse=True)
def setup_dynamodb_data(request):
    """Insert test data into DynamoDB before tests and optionally clean up after."""
    logger.info("[⚙] Connecting to DynamoDB table: %s in region %s", DYNAMODB_TABLE_NAME, AWS_REGION)
    logger.info("[TEST] DynamoDB fixture executing — REGION: %s, TABLE: %s", AWS_REGION, DYNAMODB_TABLE_NAME)
    logger.info("[TEST] Seed file path: %s → Exists: %s", DYNAMO_DATA_PATH, DYNAMO_DATA_PATH.exists())
    import botocore.exceptions

    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        _ = table.table_status  # Force connection check
    except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
        pytest.skip(f"[x] DynamoDB not accessible: {e}")

    if not DYNAMO_DATA_PATH.exists():
        pytest.skip(f"[x] Test data file not found: {DYNAMO_DATA_PATH}")
    else:
        logger.info("[✓] Found test data file: %s", DYNAMO_DATA_PATH)

    with DYNAMO_DATA_PATH.open() as f:
        items = json.load(f)

    logger.info("[→] Inserting %d items into DynamoDB...", len(items))
    success_count = 0
    for item in items:
        try:
            table.put_item(Item=item)
            success_count += 1
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError):
            logger.exception("[x] Failed to insert item %s due to BotoCoreError", item.get("PK", "<unknown>"))

    logger.info("[✓] Inserted %d/%d items", success_count, len(items))

    yield

    # Handle tear-down based on --keep-seed flag
    if request.config.getoption("--keep-seed"):
        logger.info("[↩] Skipping DynamoDB cleanup due to --keep-seed flag")
        return

    logger.info("[🧹] Deleting seeded items from DynamoDB...")
    delete_count = 0
    for item in items:
        try:
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
            delete_count += 1
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError):
            logger.exception("[x] Failed to delete item %s", item.get("PK", "<unknown>"))
    logger.info("[✓] Deleted %d/%d items", delete_count, len(items))
