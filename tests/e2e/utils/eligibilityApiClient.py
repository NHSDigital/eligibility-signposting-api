import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

import boto3
import requests
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from requests import Response


class EligibilityApiClient:
    def __init__(self, api_url: str, cert_dir: str = "tests/e2e/certs") -> None:
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

        self.api_url: str = api_url
        self.region: Optional[str] = os.getenv("AWS_REGION")
        self.aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_session_token: Optional[str] = os.getenv("AWS_SESSION_TOKEN")

        self.cert_dir: Path = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)

        self.cert_paths: Dict[str, Path] = {
            "private_key": self.cert_dir / "api_private_key_cert.pem",
            "client_cert": self.cert_dir / "api_client_cert.pem",
            "ca_cert": self.cert_dir / "api_ca_cert.pem",
        }

        self.ssm_params: Dict[str, str] = {
            "private_key": "/test/mtls/api_private_key_cert",
            "client_cert": "/test/mtls/api_client_cert",
            "ca_cert": "/test/mtls/api_ca_cert",
        }

        self._ensure_certs_present()

    def _get_ssm_parameter(self, param_name: str, decrypt: bool = True) -> str:
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
            raise RuntimeError(f"Error retrieving {param_name} from SSM: {e}") from e

    def _ensure_certs_present(self) -> None:
        missing = [k for k, path in self.cert_paths.items() if not path.exists()]
        if not missing:
            return

        for cert_type in missing:
            param_name = self.ssm_params[cert_type]
            cert_value = self._get_ssm_parameter(param_name)
            with open(self.cert_paths[cert_type], "w", encoding="utf-8") as f:
                f.write(cert_value)

    def make_request(
            self,
            nhs_number: str,
            method: str = "GET",
            payload: Optional[Union[Dict[str, Any], list]] = None,
            headers: Optional[Dict[str, str]] = None,
            strict_ssl: bool = False,
            raise_on_error: bool = True,
    ) -> Dict[str, Any]:
        url = f"{self.api_url.rstrip('/')}/{nhs_number}"
        cert = (
            str(self.cert_paths["client_cert"]),
            str(self.cert_paths["private_key"]),
        )
        verify: Union[bool, str] = str(self.cert_paths["ca_cert"]) if strict_ssl else False

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                cert=cert,
                verify=verify,
                json=payload,
                headers=headers,
                timeout=10,
            )

            if raise_on_error:
                response.raise_for_status()

            return self._parse_response(response)

        except requests.exceptions.SSLError as ssl_err:
            raise RuntimeError(f"SSL error during request: {ssl_err}") from ssl_err
        except requests.exceptions.RequestException as req_err:
            response = getattr(req_err, "response", None)
            if isinstance(response, Response):
                return self._parse_response(response)
            raise RuntimeError(f"Request error: {req_err}") from req_err

    def make_request_old(
            self,
            nhs_number: str,
            method: str = "GET",
            payload: Optional[Union[Dict[str, Any], list]] = None,
            strict_ssl: bool = False,
            raise_on_error: bool = True,
    ) -> Dict[str, Any]:
        url = f"{self.api_url.rstrip('/')}/{nhs_number}"
        cert = (
            str(self.cert_paths["client_cert"]),
            str(self.cert_paths["private_key"]),
        )
        verify: Union[bool, str] = str(self.cert_paths["ca_cert"]) if strict_ssl else False

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
            raise RuntimeError(f"SSL error during request: {ssl_err}") from ssl_err
        except requests.exceptions.RequestException as req_err:
            response = getattr(req_err, "response", None)
            if isinstance(response, Response):
                return self._parse_response(response)
            raise RuntimeError(f"Request error: {req_err}") from req_err

    def _parse_response(self, response: Response) -> Dict[str, Any]:
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

    def _clean_response(self, data: Any) -> Any:
        keys_to_ignore = ["responseId", "lastUpdated"]
        return self._remove_volatile_fields(data, keys_to_ignore)

    def _remove_volatile_fields(
            self, data: Union[Dict[str, Any], list, Any], keys_to_remove: list
    ) -> Any:
        if isinstance(data, dict):
            return {
                key: self._remove_volatile_fields(value, keys_to_remove)
                for key, value in data.items()
                if key not in keys_to_remove
            }
        elif isinstance(data, list):
            return [self._remove_volatile_fields(item, keys_to_remove) for item in data]
        return data
