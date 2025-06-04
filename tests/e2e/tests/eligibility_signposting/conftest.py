"""Pytest fixtures for the Eligibility Signposting API tests."""
import pytest
from utils.api_client import ApiClient
from utils.config import VALID_NHS_NUMBER, INVALID_NHS_NUMBER


@pytest.fixture
def api_client():
    """Create and return an instance of the API client.

    Returns:
        ApiClient: Instance of the API client.
    """
    return ApiClient()


@pytest.fixture
def valid_nhs_number():
    """Return a valid NHS number for testing.

    Returns:
        str: Valid NHS number.
    """
    return VALID_NHS_NUMBER


@pytest.fixture
def invalid_nhs_number():
    """Return an invalid NHS number for testing.

    Returns:
        str: Invalid NHS number.
    """
    return INVALID_NHS_NUMBER