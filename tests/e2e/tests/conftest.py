import json
import logging
import os
from pathlib import Path

import boto3
import pytest
from dotenv import load_dotenv

from tests.e2e.utils.eligibility_api_client import EligibilityApiClient
from tests.e2e.utils.s3_config_manager import upload_configs_to_s3

# Load environment variables from .env.local
load_dotenv(dotenv_path=".env")

# Constants
BASE_URL = os.getenv("BASE_URL", "https://test.eligibility-signposting-api.nhs.uk/patient-check")
API_KEY = os.getenv("API_KEY", "")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "eligibility_data_store")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")

# Resolve test data path robustly
BASE_DIR = Path(__file__).resolve().parent.parent
DYNAMO_DATA_PATH = BASE_DIR / "data" / "dynamoDB" / "test_data.json"

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def eligibility_client():
    return EligibilityApiClient(BASE_URL, cert_dir="certs")


@pytest.fixture
def get_scenario_params(request):
    _ = request

    def _setup(scenario, config_path):
        nhs_number = scenario["nhs_number"]
        config_filenames = scenario.get("config_filenames", [])
        request_headers = scenario.get("request_headers", {})
        query_params = scenario.get("query_params", {})

        upload_configs_to_s3(config_filenames, config_path)

        return nhs_number, config_filenames, request_headers, query_params

    return _setup
