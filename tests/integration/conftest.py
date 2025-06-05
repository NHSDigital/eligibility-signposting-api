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

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.repos.campaign_repo import BucketName
from eligibility_signposting_api.repos.person_repo import TableName
from tests.fixtures.builders.model import rule
from tests.fixtures.builders.repos.person import person_rows_builder

if TYPE_CHECKING:
    from pytest_docker.plugin import Services

logger = logging.getLogger(__name__)

AWS_REGION = "eu-west-1"


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
                    "S3_ENDPOINT": os.getenv("LOCALSTACK_INTERNAL_ENDPOINT", "http://localstack:4566/"),
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
def person_table(dynamodb_resource: ServiceResource) -> Generator[Any]:
    table = dynamodb_resource.create_table(
        TableName=TableName(os.getenv("PERSON_TABLE_NAME", "test_eligibility_datastore")),
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
def persisted_person(person_table: Any, faker: Faker) -> Generator[eligibility.NHSNumber]:
    nhs_number = eligibility.NHSNumber(faker.nhs_number())
    date_of_birth = eligibility.DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=65))

    for row in (rows := person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_77yo_person(person_table: Any, faker: Faker) -> Generator[eligibility.NHSNumber]:
    nhs_number = eligibility.NHSNumber(faker.nhs_number())
    date_of_birth = eligibility.DateOfBirth(faker.date_of_birth(minimum_age=77, maximum_age=77))

    for row in (rows := person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1", "cohort2"])):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_no_cohorts(person_table: Any, faker: Faker) -> Generator[eligibility.NHSNumber]:
    nhs_number = eligibility.NHSNumber(faker.nhs_number())

    for row in (rows := person_rows_builder(nhs_number)):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_pc_sw19(person_table: Any, faker: Faker) -> Generator[eligibility.NHSNumber]:
    nhs_number = eligibility.NHSNumber(
        faker.nhs_number(),
    )
    for row in (rows := person_rows_builder(nhs_number, postcode="SW19", cohorts=["cohort1"])):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture(scope="session")
def bucket(s3_client: BaseClient) -> Generator[BucketName]:
    bucket_name = BucketName(os.getenv("RULES_BUCKET_NAME", "test-rules-bucket"))
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
    yield bucket_name
    s3_client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(scope="session")
def campaign_config(s3_client: BaseClient, bucket: BucketName) -> Generator[rules.CampaignConfig]:
    campaign: rules.CampaignConfig = rule.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule.IterationFactory.build(
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(type=rules.RuleType.filter),
                    rule.PersonAgeSuppressionRuleFactory.build(),
                ],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort1",
                        cohort_group="cohort_group1",
                        positive_description="positive_description",
                        negative_description="negative_description",
                    )
                ],
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=bucket, Key=f"{campaign.name}.json")
