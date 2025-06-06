import os

import pytest
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
BASE_URL = os.getenv("BASE_URL", "https://sandbox.api.service.nhs.uk/eligibility-signposting-api")
API_KEY = os.getenv("API_KEY", "")
VALID_NHS_NUMBER = os.getenv("VALID_NHS_NUMBER", "50000000004")
HTTP_STATUS_SERVER_ERROR = 500


@pytest.fixture(scope="session", autouse=True)
def check_api_accessibility():
    """Check if the API is accessible before running tests."""
    try:
        response = requests.get(
            f"{BASE_URL}/eligibility-check",
            params={"patient": VALID_NHS_NUMBER},
            headers={"apikey": API_KEY, "Accept": "application/json"},
            timeout=5,
        )
        # If we get a 4xx response, the API is accessible but our request is invalid
        # If we get a 5xx response, the API is having issues
        if response.status_code >= HTTP_STATUS_SERVER_ERROR:
            pytest.skip("API is returning server errors")
    except (requests.RequestException, requests.Timeout):
        pytest.skip("API is not accessible")
