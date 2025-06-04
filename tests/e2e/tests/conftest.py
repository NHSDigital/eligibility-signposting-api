import json
import os
from pathlib import Path

import boto3
import pytest
import requests
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv(dotenv_path=".env.local")

# Constants
BASE_URL = os.getenv("BASE_URL", "https://sandbox.api.service.nhs.uk/eligibility-signposting-api")
API_KEY = os.getenv("API_KEY", "")
VALID_NHS_NUMBER = os.getenv("VALID_NHS_NUMBER", "50000000004")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "eligibilty_data_store")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")

# Resolve test data path robustly
BASE_DIR = Path(__file__).resolve().parent.parent
DYNAMO_DATA_PATH = BASE_DIR / "data" / "dynamoDB" / "test_data.json"

def pytest_addoption(parser):
    parser.addoption(
        "--keep-seed",
        action="store_true",
        default=False,
        help="Keep DynamoDB seed data after tests"
    )

@pytest.fixture(scope="session", autouse=True)
def setup_dynamodb_data(request):
    """Insert test data into DynamoDB before tests and optionally clean up after."""
    print(f"[⚙] Connecting to DynamoDB table: {DYNAMODB_TABLE_NAME} in region {AWS_REGION}")
    print(f"[TEST] DynamoDB fixture executing — REGION: {AWS_REGION}, TABLE: {DYNAMODB_TABLE_NAME}")
    print(f"[TEST] Seed file path: {DYNAMO_DATA_PATH} → Exists: {DYNAMO_DATA_PATH.exists()}")
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        _ = table.table_status  # Force connection check
    except Exception as e:
        pytest.skip(f"[x] DynamoDB not accessible: {e}")

    if not DYNAMO_DATA_PATH.exists():
        pytest.skip(f"[x] Test data file not found: {DYNAMO_DATA_PATH}")
    else:
        print(f"[✓] Found test data file: {DYNAMO_DATA_PATH}")

    with open(DYNAMO_DATA_PATH, "r") as f:
        items = json.load(f)

    print(f"[→] Inserting {len(items)} items into DynamoDB...")
    success_count = 0
    for item in items:
        try:
            table.put_item(Item=item)
            success_count += 1
        except Exception as e:
            print(f"[x] Failed to insert item {item.get('PK', '<unknown>')}: {e}")
    print(f"[✓] Inserted {success_count}/{len(items)} items")

    yield

    # Handle teardown based on --keep-seed flag
    if request.config.getoption("--keep-seed"):
        print("[↩] Skipping DynamoDB cleanup due to --keep-seed flag")
        return

    print("[🧹] Deleting seeded items from DynamoDB...")
    delete_count = 0
    for item in items:
        try:
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
            delete_count += 1
        except Exception as e:
            print(f"[x] Failed to delete item {item.get('PK', '<unknown>')}: {e}")
    print(f"[✓] Deleted {delete_count}/{len(items)} items")