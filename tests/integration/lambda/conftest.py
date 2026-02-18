import subprocess
from pathlib import Path
from typing import Callable

import pytest
from yarl import URL

from tests.integration.conftest import is_responsive


@pytest.fixture(scope="session")
def lambda_zip() -> Path:
    # Determine project root (directory containing this conftest.py)
    project_root = Path(__file__).resolve().parents[3]

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
def lambda_runtime_url(request: pytest.FixtureRequest, lambda_zip: Path) -> URL:
    docker_services = request.getfixturevalue("docker_services")
    docker_ip = request.getfixturevalue("docker_ip")

    wait_for_zip_in_container(docker_services, "lambda-api", "/tmp/lambda.zip")
    force_lambda_reload(docker_services)

    port = docker_services.port_for("lambda-api", 8080)
    base_url = URL(f"http://{docker_ip}:{port}")

    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=1.0,
        check=lambda: is_responsive(base_url)
    )
    return base_url


@pytest.fixture(scope="session")
def api_gateway_endpoint(request: pytest.FixtureRequest, lambda_runtime_url) -> URL:
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

def wait_for_zip_in_container(docker_services, service: str, path: str) -> None:
    def _check() -> bool:
        try:
            docker_services._docker_compose.execute(
                f"exec {service} test -f {path}"
            )
            return True
        except Exception:
            return False

    docker_services.wait_until_responsive(
        timeout=30,
        pause=1,
        check=_check,
    )


def force_lambda_reload(docker_services):
    # Stop and remove lambda-api
    docker_services._docker_compose.execute(f"stop lambda-api")
    docker_services._docker_compose.execute(f"rm -f lambda-api")

    # Start lambda-api fresh so it re-reads the mounted ZIP
    docker_services._docker_compose.execute(f"up --build -d lambda-api")


@pytest.fixture
def lambda_logs(docker_services) -> Callable[[], list[str]]:
    def _get_messages() -> list[str]:
        return get_lambda_logs(docker_services)

    return _get_messages


def get_lambda_logs(docker_services) -> list[str]:
    result: bytes = docker_services._docker_compose.execute("logs --no-color lambda-api")
    raw_lines = result.decode("utf-8").splitlines()
    return [line.partition("|")[-1].strip() for line in raw_lines]

