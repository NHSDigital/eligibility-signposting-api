import os
import subprocess
from pathlib import Path
from typing import Callable

import pytest
from boto3 import Session
from botocore.client import BaseClient
from yarl import URL

from tests.integration.conftest import is_responsive


def get_project_root() -> Path:
    """Finds the project root by looking for the 'dist' directory or a git folder."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "dist").exists() or (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[3]

@pytest.fixture(scope="session")
def lambda_zip() -> Path:
    project_root = get_project_root()

    build_result = subprocess.run(
        ["make", "build"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    if build_result.returncode != 0:
        pytest.fail(
            f"'make build' failed with code {build_result.returncode}.\n"
            f"STDOUT: {build_result.stdout}\n"
            f"STDERR: {build_result.stderr}"
        )

    zip_path = project_root / "dist/lambda.zip"
    if not zip_path.exists():
        pytest.fail(f"Build succeeded but {zip_path} was not created.")

    return zip_path

@pytest.fixture(scope="session")
def lambda_runtime_url(request, lambda_zip):
    """
    kick-starts the lambda simulation
    """
    docker_services = request.getfixturevalue("docker_services")
    docker_ip = request.getfixturevalue("docker_ip")
    project_root = get_project_root()
    compose_file = project_root / "tests/docker-compose.yml"

    env = os.environ.copy()
    env["COMPOSE_PROFILES"] = "lambda-test"

    subprocess.run(
        [
            "docker", "compose",
            "-f", str(compose_file),
            "up", "-d", "--build", "--force-recreate",
            "lambda-api", "api-gateway-mock",
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    port = docker_services.port_for("lambda-api", 8080)
    base_url = URL(f"http://{docker_ip}:{port}")

    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.5, check=lambda: is_responsive(base_url)
    )

    return base_url



@pytest.fixture(scope="session")
def lambda_client(boto3_session: Session, lambda_runtime_url: URL) -> BaseClient:
    return boto3_session.client("lambda", endpoint_url=str(lambda_runtime_url))

@pytest.fixture(scope="session")
def api_gateway_endpoint(request: pytest.FixtureRequest, lambda_runtime_url) -> URL:
    """
        kick-starts the api-gateway lambda simulation
    """
    docker_services = request.getfixturevalue("docker_services")
    docker_ip = request.getfixturevalue("docker_ip")

    port = docker_services.port_for("api-gateway-mock", 9123)

    base_url = URL(f"http://{docker_ip}:{port}")
    health_url = URL(f"http://{docker_ip}:{port}/health")

    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=1.0,
        check=lambda: is_responsive(health_url)
    )
    return base_url


@pytest.fixture
def lambda_logs(docker_services) -> Callable[[], list[str]]:
    """Returns a callable that fetches the latest lambda-api logs,
    allowing tests to inspect runtime output on demand."""

    def _get_messages() -> list[str]:
        return get_lambda_logs(docker_services)

    return _get_messages


def get_lambda_logs(docker_services) -> list[str]:
    """returns logs from lambda-api container"""

    result: bytes = docker_services._docker_compose.execute("logs --no-color lambda-api")
    raw_lines = result.decode("utf-8").splitlines()
    return [line.partition("|")[-1].strip() for line in raw_lines]

