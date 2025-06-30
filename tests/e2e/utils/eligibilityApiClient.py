import os
import json
import boto3
import requests
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError

class EligibilityApiClient:
    def __init__(self, api_url: str, cert_dir="tests/e2e/certs"):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

        self.api_url = api_url
        self.region = os.getenv("AWS_REGION")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_session_token = os.getenv("AWS_SESSION_TOKEN")

        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)

        self.cert_paths = {
            "private_key": self.cert_dir / "api_private_key_cert.pem",
            "client_cert": self.cert_dir / "api_client_cert.pem",
            "ca_cert": self.cert_dir / "api_ca_cert.pem"
        }

        self.ssm_params = {
            "private_key": "/test/mtls/api_private_key_cert",
            "client_cert": "/test/mtls/api_client_cert",
            "ca_cert": "/test/mtls/api_ca_cert"
        }

        self._ensure_certs_present()

    def _get_ssm_parameter(self, param_name: str, decrypt=True) -> str:
        try:
            client = boto3.client(
                "ssm",
                region_name=self.region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_session_token=self.aws_session_token,
            )
            response = client.get_parameter(Name=param_name, WithDecryption=decrypt)
            return response["Parameter"]["Value"]
        except ClientError as e:
            raise RuntimeError(f"Error retrieving {param_name} from SSM: {e}")

    def _ensure_certs_present(self):
        missing = [k for k, path in self.cert_paths.items() if not path.exists()]
        if not missing:
            return

        for cert_type in missing:
            param_name = self.ssm_params[cert_type]
            cert_value = self._get_ssm_parameter(param_name)
            with open(self.cert_paths[cert_type], "w") as f:
                f.write(cert_value)

    def make_request(
        self,
        nhs_number: str,
        method="GET",
        payload=None,
        strict_ssl=False,
        raise_on_error=True,
    ):
        url = f"{self.api_url.rstrip('/')}/{nhs_number}"
        cert = (str(self.cert_paths["client_cert"]), str(self.cert_paths["private_key"]))
        verify = str(self.cert_paths["ca_cert"]) if strict_ssl else False

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                cert=cert,
                verify=verify,
                json=payload,
                timeout=10,
            )

            if raise_on_error:
                response.raise_for_status()

            return self._parse_response(response)

        except requests.exceptions.SSLError as ssl_err:
            raise RuntimeError(f"SSL error during request: {ssl_err}")
        except requests.exceptions.RequestException as req_err:
            if response := getattr(req_err, 'response', None):
                return self._parse_response(response)
            raise RuntimeError(f"Request error: {req_err}")

    def _parse_response(self, response: requests.Response):
        try:
            data = response.json()
            cleaned = self._clean_response(data)
        except json.JSONDecodeError:
            cleaned = response.text

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": cleaned,
            "ok": response.ok,
        }

    def _clean_response(self, data: dict) -> dict:
        keys_to_ignore = ["responseId", "lastUpdated"]
        return self._remove_volatile_fields(data, keys_to_ignore)

    def _remove_volatile_fields(self, data, keys_to_remove):
        if isinstance(data, dict):
            return {
                key: self._remove_volatile_fields(value, keys_to_remove)
                for key, value in data.items()
                if key not in keys_to_remove
            }
        elif isinstance(data, list):
            return [self._remove_volatile_fields(item, keys_to_remove) for item in data]
        return data
