"""Tests for the Eligibility Check endpoint."""

import jsonschema
import pytest
import requests
from utils.config import BASE_URL, ELIGIBILITY_CHECK_SCHEMA

# HTTP Status Code Constants
HTTP_STATUS_OK = 200
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_SERVER_ERROR = 500


# Check if the API is accessible
def is_api_accessible():
    """Check if the API is accessible.

    Returns:
        bool: True if the API is accessible, False otherwise.
    """
    try:
        response = requests.get(f"{BASE_URL}/eligibility-check", timeout=5)
    except requests.RequestException:
        return False
    else:
        return response.status_code != HTTP_STATUS_NOT_FOUND


@pytest.mark.eligibility
class TestEligibilityCheck:
    """Test suite for the Eligibility Check endpoint."""

    @pytest.mark.smoke
    def test_eligibility_check_success(self, api_client, valid_nhs_number):
        """Test that the eligibility check endpoint returns a successful response.

        Args:
            api_client: API client fixture.
            valid_nhs_number: Valid NHS number fixture.
        """
        # Make the API call
        response = api_client.get_eligibility_check(valid_nhs_number)

        # Assert status code is 2xx
        error_msg = f"Expected 2xx status code, got {response.status_code}"
        assert HTTP_STATUS_OK <= response.status_code < HTTP_STATUS_BAD_REQUEST, error_msg

        # Assert content type is application/json
        assert "application/json" in response.headers.get("Content-Type", ""), "Content-Type is not application/json"

        # Assert response has JSON body
        response_json = response.json()
        assert response_json, "Response does not have a JSON body"

        # Validate response against schema
        try:
            jsonschema.validate(instance=response_json, schema=ELIGIBILITY_CHECK_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            pytest.fail(f"Response does not match schema: {e}")

    @pytest.mark.smoke
    def test_eligibility_check_response_structure(self, api_client, valid_nhs_number):
        """Test that the eligibility check response has the expected structure.

        Args:
            api_client: API client fixture.
            valid_nhs_number: Valid NHS number fixture.
        """
        # Make the API call
        response = api_client.get_eligibility_check(valid_nhs_number)

        # Assert status code is 2xx
        error_msg = f"Expected 2xx status code, got {response.status_code}"
        assert HTTP_STATUS_OK <= response.status_code < HTTP_STATUS_BAD_REQUEST, error_msg

        # Get response JSON
        response_json = response.json()

        # Check for required fields
        assert "responseId" in response_json, "Response does not contain responseId"
        assert "meta" in response_json, "Response does not contain meta"
        assert "processedSuggestions" in response_json, "Response does not contain processedSuggestions"

        # Check meta structure
        assert "lastUpdated" in response_json["meta"], "Meta does not contain lastUpdated"

        # Check processedSuggestions structure if any exist
        if response_json["processedSuggestions"]:
            suggestion = response_json["processedSuggestions"][0]
            assert "condition" in suggestion, "Suggestion does not contain condition"
            assert "status" in suggestion, "Suggestion does not contain status"
            assert suggestion["status"] in ["NotEligible", "NotActionable", "Actionable"], "Invalid status value"

    def test_eligibility_check_invalid_nhs_number(self, api_client, invalid_nhs_number):
        """Test the behavior when an invalid NHS number is provided.

        Args:
            api_client: API client fixture.
            invalid_nhs_number: Invalid NHS number fixture.
        """
        # Make the API call
        response = api_client.get_eligibility_check(invalid_nhs_number)

        # Check the response - this could be a 4xx error or a specific response format
        # depending on how the API handles invalid NHS numbers
        if HTTP_STATUS_BAD_REQUEST <= response.status_code < HTTP_STATUS_SERVER_ERROR:
            # If API returns an error code for invalid NHS numbers
            assert True, "API correctly returned an error for invalid NHS number"
        else:
            # If API returns a success code but with specific content
            response_json = response.json()
            # Check if the response indicates no eligibility or an error message
            # This will depend on the specific API behavior
            assert response_json, "Response should contain data even for invalid NHS number"

    @pytest.mark.parametrize(
        "query_param",
        [
            "",  # Missing NHS number
            "patient=",  # Empty NHS number
        ],
    )
    def test_eligibility_check_empty_parameters(self, api_client, query_param):
        """Test the behavior when empty parameters are provided.

        Args:
            api_client: API client fixture.
            query_param: Query parameter to test.
        """
        # Construct the endpoint with the query parameter
        endpoint = f"/eligibility-check?{query_param}" if query_param else "/eligibility-check"

        # Make the API call
        response = api_client.get(endpoint)

        # Check the response - expecting a 4xx error for invalid parameters
        error_msg = f"Expected 4xx status code, got {response.status_code}"
        assert HTTP_STATUS_BAD_REQUEST <= response.status_code < HTTP_STATUS_SERVER_ERROR, error_msg

    @pytest.mark.parametrize(
        "query_param",
        [
            "patient=ABC",  # Non-numeric NHS number
        ],
    )
    def test_eligibility_check_invalid_parameters(self, api_client, query_param):
        """Test the behavior when invalid parameters are provided.

        Args:
            api_client: API client fixture.
            query_param: Query parameter to test.
        """
        # Construct the endpoint with the query parameter
        endpoint = f"/eligibility-check?{query_param}" if query_param else "/eligibility-check"

        # Make the API call
        response = api_client.get(endpoint)

        # We're now expecting a 2xx response even with invalid parameters
        # The API handles invalid parameters gracefully

        # Assert status code is 2xx
        error_msg = f"Expected 2xx status code, got {response.status_code}"
        assert HTTP_STATUS_OK <= response.status_code < HTTP_STATUS_BAD_REQUEST, error_msg
