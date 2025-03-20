import logging
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import boto3
import httpx
import pytest
import stamina
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from httpx import RequestError
from yarl import URL

logger = logging.getLogger(__name__)

AWS_REGION = "eu-west-1"


@pytest.fixture(scope="session")
def localstack(request) -> URL:
    if url := os.getenv("RUNNING_LOCALSTACK_URL", None):
        logger.info("localstack already running on %s", url)
        return URL(url)

    docker_ip = request.getfixturevalue("docker_ip")
    docker_services = request.getfixturevalue("docker_services")

    logger.info("Starting localstack")
    port = docker_services.port_for("localstack", 4566)
    url = URL(f"http://{docker_ip}:{port}")
    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=lambda: is_responsive(url))
    logger.info("localstack running on %s", url)
    return url


def is_responsive(url: URL) -> bool:
    try:
        response = httpx.get(str(url))
        response.raise_for_status()
    except RequestError:
        return False
    else:
        return True


@pytest.fixture(scope="session")
def lambda_client(localstack: URL) -> BaseClient:
    return boto3.client(
        "lambda",
        endpoint_url=str(localstack),
        region_name=AWS_REGION,
        aws_access_key_id="fake",
        aws_secret_access_key="fake",
    )


@pytest.fixture(scope="session")
def dynamodb_client(localstack: URL) -> BaseClient:
    return boto3.client(
        "dynamodb",
        endpoint_url=str(localstack),
        region_name=AWS_REGION,
        aws_access_key_id="fake",
        aws_secret_access_key="fake",
    )


@pytest.fixture(scope="session")
def dynamodb_resource(localstack: URL) -> ServiceResource:
    return boto3.resource(
        "dynamodb",
        endpoint_url=str(localstack),
        region_name=AWS_REGION,
        aws_access_key_id="fake",
        aws_secret_access_key="fake",
    )


@pytest.fixture(scope="session")
def flask_function(lambda_client: BaseClient) -> str:
    function_name = "flask_function"
    with Path("dist/lambda.zip").open("rb") as zipfile:
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.13",
            Role="arn:aws:iam::123456789012:role/test-role",
            Handler="eligibility_signposting_api.app.lambda_handler",
            Code={"ZipFile": zipfile.read()},
            Architectures=["x86_64"],
            Timeout=180,
            Environment={
                "Variables": {
                    "DYNAMODB_ENDPOINT": os.getenv("LOCALSTACK_INTERNAL_ENDPOINT", "http://localstack:4566/"),
                    "AWS_REGION": AWS_REGION,
                }
            },
        )
    logger.info("loaded zip")
    wait_for_function_active(function_name, lambda_client)
    logger.info("function active")
    return function_name


@pytest.fixture(scope="session")
def flask_function_url(lambda_client: BaseClient, flask_function: str) -> URL:
    response = lambda_client.create_function_url_config(FunctionName=flask_function, AuthType="NONE")
    return URL(response["FunctionUrl"])


class FunctionNotActiveError(Exception):
    """Lambda Function not yet active"""


def wait_for_function_active(function_name, lambda_client):
    for attempt in stamina.retry_context(on=FunctionNotActiveError):
        with attempt:
            logger.info("waiting")
            response = lambda_client.get_function(FunctionName=function_name)
            function_state = response["Configuration"]["State"]
            logger.info("function_state %s", function_state)
            if function_state != "Active":
                raise FunctionNotActiveError


@pytest.fixture(scope="session")
def people_table(dynamodb_resource: ServiceResource) -> Generator[Any]:
    table = dynamodb_resource.create_table(
        TableName="People",
        KeySchema=[{"AttributeName": "name", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "name", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table.wait_until_exists()
    yield table
    table.delete()
    table.wait_until_not_exists()
