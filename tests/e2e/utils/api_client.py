"""API client module for making HTTP requests to the Eligibility Signposting API."""

import requests
from utils.config import API_KEY, BASE_URL

# Default timeout for API requests in seconds
DEFAULT_TIMEOUT = 10


class ApiClient:
    """API client for making HTTP requests to the Eligibility Signposting API."""

    def __init__(self, base_url=BASE_URL, api_key=API_KEY):
        """Initialize the API client with base URL and API key.

        Args:
            base_url (str, optional): Base URL for the API. Defaults to BASE_URL from config.
            api_key (str, optional): API key for authentication. Defaults to API_KEY from config.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Accept": "application/json", "apikey": self.api_key}

    def get_eligibility_check(self, nhs_number):
        """Make a GET request to the eligibility-check endpoint.

        Args:
            nhs_number (str): NHS number to check eligibility for.

        Returns:
            requests.Response: Response object from the API.
        """
        url = f"{BASE_URL}/patient-check/{nhs_number}"
        params = {"patient": nhs_number}

        return requests.get(url, headers=self.headers, params=params, timeout=DEFAULT_TIMEOUT)

    def get(self, endpoint, params=None):
        """Make a generic GET request to the API.

        Args:
            endpoint (str): API endpoint to call.
            params (dict, optional): Query parameters. Defaults to None.

        Returns:
            requests.Response: Response object from the API.
        """
        url = f"{self.base_url}{endpoint}"
        return requests.get(url, headers=self.headers, params=params, timeout=DEFAULT_TIMEOUT)

    def post(self, endpoint, data=None, json=None):
        """Make a generic POST request to the API.

        Args:
            endpoint (str): API endpoint to call.
            data (dict, optional): Form data. Defaults to None.
            json (dict, optional): JSON data. Defaults to None.

        Returns:
            requests.Response: Response object from the API.
        """
        url = f"{self.base_url}{endpoint}"
        return requests.post(url, headers=self.headers, data=data, json=json, timeout=DEFAULT_TIMEOUT)
