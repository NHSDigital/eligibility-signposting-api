import json
import logging
import os
import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import stamina
from boto3 import Session
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from faker import Faker
from httpx import RequestError
from yarl import URL

from eligibility_signposting_api.model.eligibility import DateOfBirth, NHSNumber, Postcode
from eligibility_signposting_api.model.rules import (
    BucketName,
    CampaignConfig,
    RuleAttributeLevel,
    RuleOperator,
    RuleType,
)
from tests.utils.builders import CampaignConfigFactory, IterationFactory, IterationRuleFactory

if TYPE_CHECKING:
    from pytest_docker.plugin import Services

logger = logging.getLogger(__name__)

AWS_REGION = "eu-west-1"


@pytest.fixture(scope="session")
def faker() -> Faker:
    return Faker("en_UK")


@pytest.fixture(scope="session")
def localstack(request: pytest.FixtureRequest) -> URL:
    if url := os.getenv("RUNNING_LOCALSTACK_URL", None):
        logger.info("localstack already running on %s", url)
        return URL(url)

    docker_ip: str = request.getfixturevalue("docker_ip")
    docker_services: Services = request.getfixturevalue("docker_services")

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
def boto3_session() -> Session:
    return Session(aws_access_key_id="fake", aws_secret_access_key="fake", region_name=AWS_REGION)


@pytest.fixture(scope="session")
def lambda_client(boto3_session: Session, localstack: URL) -> BaseClient:
    return boto3_session.client("lambda", endpoint_url=str(localstack))


@pytest.fixture(scope="session")
def dynamodb_client(boto3_session: Session, localstack: URL) -> BaseClient:
    return boto3_session.client("dynamodb", endpoint_url=str(localstack))


@pytest.fixture(scope="session")
def dynamodb_resource(boto3_session: Session, localstack: URL) -> ServiceResource:
    return boto3_session.resource("dynamodb", endpoint_url=str(localstack))


@pytest.fixture(scope="session")
def logs_client(boto3_session: Session, localstack: URL) -> BaseClient:
    return boto3_session.client("logs", endpoint_url=str(localstack))


@pytest.fixture(scope="session")
def iam_client(boto3_session: Session, localstack: URL) -> BaseClient:
    return boto3_session.client("iam", endpoint_url=str(localstack))


@pytest.fixture(scope="session")
def s3_client(boto3_session: Session, localstack: URL) -> BaseClient:
    return boto3_session.client("s3", endpoint_url=str(localstack))


@pytest.fixture(scope="session")
def iam_role(iam_client: BaseClient) -> Generator[str]:
    role_name = "LambdaExecutionRole"
    policy_name = "LambdaCloudWatchPolicy"

    # Define IAM Trust Policy for Lambda Execution Role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}
        ],
    }

    # Create IAM Role
    role = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="Role for Lambda execution with CloudWatch logging permissions",
    )

    # Define IAM Policy for CloudWatch Logs
    log_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": "arn:aws:logs:*:*:*",
            }
        ],
    }

    # Create the IAM Policy
    policy = iam_client.create_policy(PolicyName=policy_name, PolicyDocument=json.dumps(log_policy))
    policy_arn = policy["Policy"]["Arn"]

    # Attach Policy to Role
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

    yield role["Role"]["Arn"]

    iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    iam_client.delete_policy(PolicyArn=policy_arn)
    iam_client.delete_role(RoleName=role_name)


@pytest.fixture(scope="session")
def lambda_zip() -> Path:
    build_result = subprocess.run(["make", "build"], capture_output=True, text=True, check=False)  # Noqa: S603, S607
    assert build_result.returncode == 0, f"'make build' failed: {build_result.stderr}"
    return Path("dist/lambda.zip")


@pytest.fixture(scope="session")
def flask_function(lambda_client: BaseClient, iam_role: str, lambda_zip: Path) -> Generator[str]:
    function_name = "eligibility_signposting_api"
    with lambda_zip.open("rb") as zipfile:
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.13",
            Role=iam_role,
            Handler="eligibility_signposting_api.app.lambda_handler",
            Code={"ZipFile": zipfile.read()},
            Architectures=["x86_64"],
            Timeout=180,
            Environment={
                "Variables": {
                    "DYNAMODB_ENDPOINT": os.getenv("LOCALSTACK_INTERNAL_ENDPOINT", "http://localstack:4566/"),
                    "AWS_REGION": AWS_REGION,
                    "LOG_LEVEL": "DEBUG",
                }
            },
        )
    logger.info("loaded zip")
    wait_for_function_active(function_name, lambda_client)
    logger.info("function active")
    yield function_name
    lambda_client.delete_function(FunctionName=function_name)


@pytest.fixture(scope="session")
def flask_function_url(lambda_client: BaseClient, flask_function: str) -> URL:
    response = lambda_client.create_function_url_config(FunctionName=flask_function, AuthType="NONE")
    return URL(response["FunctionUrl"])


class FunctionNotActiveError(Exception):
    """Lambda Function not yet active"""


def wait_for_function_active(function_name, lambda_client):
    for attempt in stamina.retry_context(on=FunctionNotActiveError, attempts=20, timeout=120):
        with attempt:
            logger.info("waiting")
            response = lambda_client.get_function(FunctionName=function_name)
            function_state = response["Configuration"]["State"]
            logger.info("function_state %s", function_state)
            if function_state != "Active":
                raise FunctionNotActiveError


@pytest.fixture(scope="session")
def eligibility_table(dynamodb_resource: ServiceResource) -> Generator[Any]:
    table = dynamodb_resource.create_table(
        TableName="eligibility_data_store",
        KeySchema=[
            {"AttributeName": "NHS_NUMBER", "KeyType": "HASH"},
            {"AttributeName": "ATTRIBUTE_TYPE", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "NHS_NUMBER", "AttributeType": "S"},
            {"AttributeName": "ATTRIBUTE_TYPE", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table.wait_until_exists()
    yield table
    table.delete()


@pytest.fixture
def persisted_person(eligibility_table: Any, faker: Faker) -> Generator[tuple[NHSNumber, DateOfBirth, Postcode]]:
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth())
    postcode = Postcode(faker.postcode())
    eligibility_table.put_item(
        Item={
            "NHS_NUMBER": f"PERSON#{nhs_number}",
            "ATTRIBUTE_TYPE": "PERSON",
            "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
            "POSTCODE": postcode,
        }
    )
    eligibility_table.put_item(
        Item={"NHS_NUMBER": f"PERSON#{nhs_number}", "ATTRIBUTE_TYPE": "COHORTS", "COHORT_MAP": {}}
    )
    yield nhs_number, date_of_birth, postcode
    eligibility_table.delete_item(Key={"NHS_NUMBER": f"PERSON#{nhs_number}", "ATTRIBUTE_TYPE": "PERSON"})
    eligibility_table.delete_item(Key={"NHS_NUMBER": f"PERSON#{nhs_number}", "ATTRIBUTE_TYPE": "COHORTS"})


@pytest.fixture(scope="session")
def bucket(s3_client: BaseClient) -> Generator[BucketName]:
    bucket_name = BucketName("test-rules-bucket")
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
    yield bucket_name
    s3_client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(scope="session")
def campaign_config(s3_client: BaseClient, bucket: BucketName) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = CampaignConfigFactory.build(
        iterations=[
            IterationFactory.build(
                iteration_rules=[
                    IterationRuleFactory.build(
                        type=RuleType.filter,
                        operator=RuleOperator.lt,
                        attribute_level=RuleAttributeLevel.PERSON,
                        attribute_name="DATE_OF_BIRTH",
                        comparator="-75",
                    )
                ]
            )
        ]
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=bucket, Key=f"{campaign.name}.json")
