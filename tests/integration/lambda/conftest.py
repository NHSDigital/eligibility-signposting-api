import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from boto3 import Session
from botocore.client import BaseClient
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
def lambda_runtime_url(request, lambda_zip):  # noqa: ARG001
    """
    Start the lambda simulation using docker compose.
    """
    docker_services = request.getfixturevalue("docker_services")
    docker_ip = request.getfixturevalue("docker_ip")
    project_root = get_project_root()
    compose_file = project_root / "tests/docker-compose.yml"

    # Activate the profile without using the --profile flag
    env = os.environ.copy()
    env["COMPOSE_PROFILES"] = "lambda-test"

    docker_path = shutil.which("docker")
    if not docker_path:
        pytest.fail("Docker executable not found in PATH")

    result = subprocess.run(  # noqa: S603
        [
            docker_path,
            "compose",
            "-f",
            str(compose_file),
            "up",
            "-d",
            "--build",
            "--force-recreate",
            "lambda-api",
            "api-gateway-mock",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(
            f"Docker compose failed with code {result.returncode}.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    port = docker_services.port_for("lambda-api", 8080)
    base_url = URL(f"http://{docker_ip}:{port}")

    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=0.5,
        check=lambda: is_responsive(base_url),
    )

    return base_url


@pytest.fixture(scope="session")
def lambda_client(boto3_session: Session, lambda_runtime_url: URL) -> BaseClient:
    """Return a boto3 Lambda client pointing at the simulated lambda runtime."""
    return boto3_session.client("lambda", endpoint_url=str(lambda_runtime_url))


@pytest.fixture(scope="session")
def api_gateway_endpoint(request: pytest.FixtureRequest, lambda_runtime_url):  # noqa: ARG001
    """
    Start and validate the API Gateway mock.
    """
    docker_services = request.getfixturevalue("docker_services")
    docker_ip = request.getfixturevalue("docker_ip")

    port = docker_services.port_for("api-gateway-mock", 9123)

    base_url = URL(f"http://{docker_ip}:{port}")
    health_url = URL(f"http://{docker_ip}:{port}/health")

    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=1.0,
        check=lambda: is_responsive(health_url),
    )

    return base_url


@pytest.fixture
def lambda_logs(docker_services) -> Callable[[], list[str]]:
    """Return a callable that fetches the latest lambda-api logs."""

    def _get_messages() -> list[str]:
        return get_lambda_logs(docker_services)

    return _get_messages


def get_lambda_logs(docker_services) -> list[str]:  # noqa :ARG001
    """Fetch logs from the lambda-api container."""
    raw_docker = shutil.which("docker")
    if not raw_docker:
        return ["Error: Docker not found"]

    docker_path = Path(raw_docker).resolve()
    project_root = get_project_root()
    compose_file = (project_root / "tests" / "docker-compose.yml").resolve()

    result = subprocess.run(  # noqa: S603
        [
            str(docker_path),
            "compose",
            "-f",
            str(compose_file),
            "logs",
            "--no-color",
            "lambda-api",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return [line.partition("|")[-1].strip() for line in result.stdout.splitlines()]
