import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

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
def api_gateway_endpoint(request, lambda_runtime_url: URL) -> URL:  # noqa: ARG001
    docker_services = request.getfixturevalue("docker_services")
    docker_ip = request.getfixturevalue("docker_ip")

    docker_services._docker_compose.execute("up -d api-gateway-mock")  # noqa: SLF001

    port = docker_services.port_for("api-gateway-mock", 9123)
    url = URL(f"http://{docker_ip}:{port}")
    health_url = url / "health"
    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=0.2,
        check=lambda: is_responsive(health_url),
    )
    return url


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
