import shutil
import subprocess
import urllib.parse
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path

import httpx
import pytest
from boto3 import Session
from botocore.client import BaseClient
from pytest_docker import Services
from yarl import URL

from tests.integration.conftest import is_responsive


def get_project_root() -> Path:
    """Find the project root by locating 'dist' or '.git'."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "dist").exists() or (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def lambda_zip() -> Path:
    """Build the lambda.zip artifact using `make build`."""
    project_root = get_project_root()

    make_path = shutil.which("make")
    if not make_path:
        pytest.fail("The 'make' executable was not found in the system PATH.")

    build_result = subprocess.run(  # noqa: S603
        [make_path, "build"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    if build_result.returncode != 0:
        pytest.fail(
            f"'make build' failed with code {build_result.returncode}.\n"
            f"STDOUT:\n{build_result.stdout}\n"
            f"STDERR:\n{build_result.stderr}"
        )

    zip_path = project_root / "dist" / "lambda.zip"
    if not zip_path.exists():
        pytest.fail(f"Build succeeded but {zip_path} was not created.")

    return zip_path


@pytest.fixture(scope="session")
def lambda_runtime_url(request, lambda_zip: Path) -> URL:  # noqa : ARG001
    docker_services = request.getfixturevalue("docker_services")
    docker_ip = request.getfixturevalue("docker_ip")

    docker_services._docker_compose.execute("up -d lambda-api")  # noqa : SLF001

    port = docker_services.port_for("lambda-api", 8080)
    base_url = URL(f"http://{docker_ip}:{port}")

    # The RIE expects this path for invocations
    health_url = base_url / "2015-03-31/functions/function/invocations"

    docker_services.wait_until_responsive(
        timeout=60.0,
        pause=2,
        check=lambda: is_responsive(health_url),
    )
    return base_url


@pytest.fixture(scope="session")
def lambda_client(boto3_session: Session, lambda_runtime_url: URL) -> BaseClient:
    """Return a boto3 Lambda client pointing at the simulated lambda runtime."""
    return boto3_session.client("lambda", endpoint_url=str(lambda_runtime_url))


def get_lambda_logs(docker_services) -> list[str]:
    """
    Fetch logs from the lambda-api container using the internal pytest-docker executor.
    This replaces manual subprocess calls and path resolution.
    """
    try:
        result = docker_services._docker_compose.execute("logs --no-color lambda-api")  # noqa: SLF001

        output = result.decode("utf-8") if isinstance(result, bytes) else str(result)

        return [line.split("|", 1)[-1].strip() for line in output.splitlines()]
    except Exception as e:  # noqa: BLE001
        return [f"Error fetching logs: {e!s}"]


@pytest.fixture
def lambda_logs(docker_services: Services) -> Callable[[], list[str]]:
    """Fixture to provide access to container logs."""

    def _get_messages() -> list[str]:
        return get_lambda_logs(docker_services)

    return _get_messages


def build_api_gateway_v2_event(path: str, headers: dict | None = None, params: dict | None = None):
    """
    Simulates the HTTP payload sent by a Lambda Function URL or API Gateway V2.
    """
    query_string = urllib.parse.urlencode(params) if params else ""
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": query_string,
        "headers": {"accept": "*/*", "content-type": "application/json", **(headers or {})},
        "queryStringParameters": params or {},
        "requestContext": {
            "http": {
                "method": "GET",
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
            },
        },
        "isBase64Encoded": False,
    }


def unwrap_lambda_response(rie_response: httpx.Response) -> httpx.Response:
    """
    Unpacks a Lambda Proxy (RIE) response into a standard httpx.Response.
    """
    data = rie_response.json()

    inner_body = data.get("body", "{}")
    inner_status = data.get("statusCode", 200)
    inner_headers = data.get("headers", {})

    unwrapped_response = httpx.Response(
        status_code=inner_status,
        content=inner_body.encode("utf-8"),
        headers=inner_headers,
        request=rie_response.request,
    )

    # Transfers timing metadata from the RIE call to the unwrapped response.
    # This prevents a RuntimeError when matchers access the .elapsed property during is_response() assertion.
    unwrapped_response._elapsed = rie_response.elapsed  # noqa: SLF001

    return unwrapped_response


@pytest.fixture
def invoke_with_mock_apigw_request(lambda_runtime_url: URL) -> Callable[..., httpx.Response]:
    """
    Fixture that returns a function to invoke the Lambda via RIE
    and returns a clean, unwrapped httpx.Response.
    """
    invocation_url = str(lambda_runtime_url / "2015-03-31/functions/function/invocations")

    def _invoke(path: str, headers: dict | None = None, params: dict | None = None) -> httpx.Response:
        payload = build_api_gateway_v2_event(path=path, headers=headers, params=params)

        rie_response = httpx.post(invocation_url, json=payload, timeout=10)

        if rie_response.status_code != HTTPStatus.OK:
            pytest.fail(f"RIE failed with {rie_response.status_code}: {rie_response.text}")

        return unwrap_lambda_response(rie_response)

    return _invoke
