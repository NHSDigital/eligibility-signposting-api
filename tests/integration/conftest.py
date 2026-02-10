import datetime
import json
import logging
import os
import subprocess
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import httpx
import pytest
from boto3 import Session
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from faker import Faker
from httpx import RequestError
from pytest_docker.plugin import Services
from yarl import URL

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import (
    AvailableAction,
    CampaignConfig,
    EndDate,
    RuleCode,
    RuleEntry,
    RuleName,
    RuleText,
    RuleType,
    StartDate,
    StatusText,
)
from eligibility_signposting_api.model.consumer_mapping import ConsumerCampaign, ConsumerId, ConsumerMapping
from eligibility_signposting_api.processors.hashing_service import HashingService, HashSecretName
from eligibility_signposting_api.repos import SecretRepo
from eligibility_signposting_api.repos.campaign_repo import BucketName
from eligibility_signposting_api.repos.person_repo import TableName
from tests.fixtures.builders.model import rule
from tests.fixtures.builders.model.rule import RulesMapperFactory
from tests.fixtures.builders.repos.person import person_rows_builder

logger = logging.getLogger(__name__)

AWS_REGION = "eu-west-1"

AWS_SECRET_NAME = "test_secret"  # noqa: S105
AWS_CURRENT_SECRET = "test_value"  # noqa: S105
AWS_PREVIOUS_SECRET = "test_value_old"  # noqa: S105
UNIQUE_CONSUMER_HEADER = "nhse-product-id"

@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["AWS_SECURITY_TOKEN"] = "fake"
    os.environ["AWS_SESSION_TOKEN"] = "fake"
    os.environ["AWS_DEFAULT_REGION"] = AWS_REGION

@pytest.fixture(scope="session")
def moto_server(request: pytest.FixtureRequest) -> URL:
    docker_ip: str = request.getfixturevalue("docker_ip")
    docker_services: Services = request.getfixturevalue("docker_services")

    logger.info("Starting moto server on %s", docker_ip)
    port = docker_services.port_for("moto-server", 5000)
    url = URL(f"http://{docker_ip}:{port}")
    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=lambda: is_responsive(url))
    logger.info("moto server is running on %s", url)
    return url

@pytest.fixture(scope="session")
def fargate_simulation(request: pytest.FixtureRequest) -> URL:
    docker_ip: str = request.getfixturevalue("docker_ip")
    docker_services: Services = request.getfixturevalue("docker_services")

    logger.info("Starting mocked fargate server on %s", docker_ip)
    port = docker_services.port_for("mock-fargate-server", 5000)
    url = URL(f"http://{docker_ip}:{port}")
    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=lambda: is_responsive(url/"patient-check/_status"))
    logger.info("fargate server is running on %s", url)
    return url

def get_fargate_logs(docker_services: Services) -> list[str]:
    result: bytes = docker_services._docker_compose.execute("logs --no-color mock-fargate-server")
    raw_lines = result.decode("utf-8").splitlines()
    # Strip the 'service-name | ' prefix that Docker Compose adds
    return [line.partition("|")[-1].strip() for line in raw_lines]

@pytest.fixture
def fargate_logs(docker_services: Services) -> Callable[[], list[str]]:
    """Fixture to provide access to container logs."""

    def _get_messages() -> list[str]:
        return get_fargate_logs(docker_services)

    return _get_messages

@pytest.fixture(scope="session")
def api_gateway_simulation(request: pytest.FixtureRequest) -> URL:
    docker_ip: str = request.getfixturevalue("docker_ip")
    docker_services: Services = request.getfixturevalue("docker_services")

    logger.info("Starting mocked aws gateway on %s", docker_ip)
    port = docker_services.port_for("mock-api-gateway", 9123)
    url = URL(f"http://{docker_ip}:{port}")
    docker_services.wait_until_responsive(timeout=30.0, pause=0.1, check=lambda: is_responsive(url/"health"))
    logger.info("fargate server is running on %s", url)
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
    return Session(aws_access_key_id="fake", aws_secret_access_key="fake", aws_session_token="fake", region_name=AWS_REGION)

@pytest.fixture(scope="session")
def api_gateway_client(boto3_session: Session, moto_server:URL) -> BaseClient:
    return boto3_session.client("apigateway", endpoint_url=str(moto_server))

@pytest.fixture(scope="session")
def dynamodb_resource(boto3_session: Session, moto_server:URL) -> BaseClient:
    return boto3_session.resource("dynamodb", endpoint_url=str(moto_server))

@pytest.fixture(scope="session")
def logs_client(boto3_session: Session, moto_server:URL) -> BaseClient:
    return boto3_session.client("logs", endpoint_url=str(moto_server))

@pytest.fixture(scope="session")
def iam_client(boto3_session: Session, moto_server:URL) -> BaseClient:
    return boto3_session.client("iam", endpoint_url=str(moto_server))


@pytest.fixture(scope="session")
def s3_client(boto3_session: Session, moto_server:URL) -> BaseClient:
    return boto3_session.client("s3", endpoint_url=str(moto_server))


@pytest.fixture(scope="session")
def firehose_client(boto3_session: Session, moto_server:URL) -> BaseClient:
    return boto3_session.client("firehose", endpoint_url=str(moto_server))


@pytest.fixture(scope="session", autouse=True)
def secretsmanager_client(boto3_session: Session, moto_server:URL) -> BaseClient:
    """
    Provides a mocked boto3 Secrets Manager client (via Moto).
    Seeds a test secret with 'Previous' and 'Current' values.
    """
    # 1. Create client without endpoint_url (Moto intercepts default AWS URLs)
    client: BaseClient = boto3_session.client("secretsmanager", endpoint_url=str(moto_server))

    # 2. Seed the initial "Previous" value
    # We use try/except to handle cases where the mock might not have fully reset
    # (though usually with Moto it starts empty).
    try:
        client.create_secret(
            Name=AWS_SECRET_NAME,
            SecretString=AWS_PREVIOUS_SECRET,
        )
    except client.exceptions.ResourceExistsException:
        client.put_secret_value(
            SecretId=AWS_SECRET_NAME,
            SecretString=AWS_PREVIOUS_SECRET,
        )

    # 3. Rotate to the "Current" value
    # This ensures the secret has version stages similar to a real rotated secret
    client.put_secret_value(
        SecretId=AWS_SECRET_NAME,
        SecretString=AWS_CURRENT_SECRET,
    )

    return client

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
    dynamodb_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:Query",
                ],
                "Resource": "arn:aws:dynamodb:*:*:table/*",
            }
        ],
    }

    # Create CloudWatch Logs policy (as before)
    log_policy_resp = iam_client.create_policy(PolicyName=policy_name, PolicyDocument=json.dumps(log_policy))
    log_policy_arn = log_policy_resp["Policy"]["Arn"]
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=log_policy_arn)

    # Create DynamoDB policy
    ddb_policy_resp = iam_client.create_policy(
        PolicyName="LambdaDynamoDBPolicy", PolicyDocument=json.dumps(dynamodb_policy)
    )
    ddb_policy_arn = ddb_policy_resp["Policy"]["Arn"]
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=ddb_policy_arn)

    yield role["Role"]["Arn"]

    iam_client.detach_role_policy(RoleName=role_name, PolicyArn=log_policy_arn)
    iam_client.delete_policy(PolicyArn=log_policy_arn)
    iam_client.detach_role_policy(RoleName=role_name, PolicyArn=ddb_policy_arn)
    iam_client.delete_policy(PolicyArn=ddb_policy_arn)
    iam_client.delete_role(RoleName=role_name)


@pytest.fixture(scope="session")
def lambda_zip() -> Path:
    build_result = subprocess.run(["make", "build"], capture_output=True, text=True, check=False)  # noqa: S607
    assert build_result.returncode == 0, f"'make build' failed: {build_result.stderr}"
    return Path("dist/lambda.zip")


@pytest.fixture(autouse=True)
def clean_audit_bucket(s3_client: BaseClient, audit_bucket: str):
    objects_to_delete = []
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=audit_bucket)
    for page in pages:
        if "Contents" in page:
            objects_to_delete.extend([{"Key": obj["Key"]} for obj in page["Contents"]])

    if objects_to_delete:
        s3_client.delete_objects(
            Bucket=audit_bucket,
            Delete={"Objects": objects_to_delete, "Quiet": True},
        )

@pytest.fixture
def api_gateway_endpoint(fargate_simulation, api_gateway_simulation, moto_server):
    return api_gateway_simulation

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
def persisted_person(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=65))

    for row in (
        rows := person_rows_builder(nhs_num_hash, date_of_birth=date_of_birth, postcode="hp1", cohorts=["cohort1"]).data
    ):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_factory(
    person_table: Any,
    faker: Faker,
    hashing_service: HashingService,
    request: pytest.FixtureRequest,
):
    created_rows: list[dict[str, Any]] = []

    def _factory(
        *,
        secret_key: str = "current",  # noqa: S107
        postcode: str = "hp1",
        cohorts: list[str] | None = None,
        minimum_age: int = 18,
        maximum_age: int = 65,
    ) -> eligibility_status.NHSNumber:
        nhs_num = faker.nhs_number()
        nhs_number = eligibility_status.NHSNumber(nhs_num)

        # hashing selector
        if secret_key == "current":  # noqa: S105
            nhs_key = hashing_service.hash_with_current_secret(nhs_num)
        elif secret_key == "previous":  # noqa: S105
            nhs_key = hashing_service.hash_with_previous_secret(nhs_num)
        elif secret_key == "not_hashed":  # noqa: S105
            nhs_key = nhs_num

        # build DOB
        date_of_birth = eligibility_status.DateOfBirth(
            faker.date_of_birth(minimum_age=minimum_age, maximum_age=maximum_age)
        )

        rows = person_rows_builder(
            nhs_key,
            date_of_birth=date_of_birth,
            postcode=postcode,
            cohorts=cohorts or ["cohort1"],
        ).data

        # persist rows
        for row in rows:
            person_table.put_item(Item=row)
            created_rows.append(row)

        return nhs_number

    # cleanup hook
    def cleanup():
        for row in created_rows:
            person_table.delete_item(
                Key={
                    "NHS_NUMBER": row["NHS_NUMBER"],
                    "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"],
                }
            )

    request.addfinalizer(cleanup)  # noqa: PT021

    return _factory


@pytest.fixture
def persisted_person_previous(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_previous_secret(nhs_num)  # AWSPREVIOUS

    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=65))

    for row in (
        rows := person_rows_builder(nhs_num_hash, date_of_birth=date_of_birth, postcode="hp1", cohorts=["cohort1"]).data
    ):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_not_hashed(
    person_table: Any,
    faker: Faker,
) -> Generator[eligibility_status.NHSNumber]:
    nhs_number = eligibility_status.NHSNumber(faker.nhs_number())
    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=65))

    for row in (
        rows := person_rows_builder(nhs_number, date_of_birth=date_of_birth, postcode="hp1", cohorts=["cohort1"]).data
    ):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_77yo_person(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=77, maximum_age=77))

    for row in (
        rows := person_rows_builder(
            nhs_num_hash,
            date_of_birth=date_of_birth,
            postcode="hp1",
            cohorts=["cohort1", "cohort2"],
        ).data
    ):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_all_cohorts(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=74, maximum_age=74))

    for row in (
        rows := person_rows_builder(
            nhs_num_hash,
            date_of_birth=date_of_birth,
            postcode="SW19",
            cohorts=["cohort_label1", "cohort_label2", "cohort_label3", "cohort_label4", "cohort_label5"],
            icb="QE1",
        ).data
    ):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def person_with_all_data(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    date_of_birth = eligibility_status.DateOfBirth(datetime.date(1990, 2, 28))

    for row in (
        rows := person_rows_builder(
            nhs_number=nhs_num_hash,
            date_of_birth=date_of_birth,
            gender="0",
            postcode="SW18",
            cohorts=["cohort_label1", "cohort_label2"],
            vaccines={"RSV": {"LAST_SUCCESSFUL_DATE": None}},
            icb="QE1",
            gp_practice="C81002",
            pcn="U78207",
            comissioning_region="Y60",
            thirteen_q=True,
            care_home=True,
            de=False,
            msoa="E02001562",
            lsoa="E01030316",
        ).data
    ):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_no_cohorts(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    for row in (rows := person_rows_builder(nhs_num_hash).data):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_pc_sw19(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    for row in (rows := person_rows_builder(nhs_num_hash, postcode="SW19", cohorts=["cohort1"]).data):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_with_no_person_attribute_type(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=65))

    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    for row in (
        rows := person_rows_builder(nhs_num_hash, date_of_birth=date_of_birth, postcode="hp1", cohorts=["cohort1"]).data
    ):
        if row["ATTRIBUTE_TYPE"] != "PERSON":
            person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def person_with_covid_vaccination(
    person_table: Any, faker: Faker, hashing_service: HashingService
) -> Generator[eligibility_status.NHSNumber]:
    """
    Fixture for a person with a COVID vaccination on 2026-01-28.
    Used for testing derived values (ADD_DAYS function).
    """
    nhs_num = faker.nhs_number()
    nhs_number = eligibility_status.NHSNumber(nhs_num)
    nhs_num_hash = hashing_service.hash_with_current_secret(nhs_num)

    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=77, maximum_age=77))

    for row in (
        rows := person_rows_builder(
            nhs_number=nhs_num_hash,
            date_of_birth=date_of_birth,
            postcode="HP1",
            cohorts=["cohort_label1"],
            vaccines={"COVID": {"LAST_SUCCESSFUL_DATE": "20260128"}},
            icb="QE1",
        ).data
    ):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture(scope="session")
def rules_bucket(s3_client: BaseClient) -> Generator[BucketName]:
    bucket_name = BucketName(os.getenv("RULES_BUCKET_NAME", "test-rules-bucket"))
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
    yield bucket_name
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    if "Contents" in response:
        objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
        s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": objects_to_delete})
    s3_client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(scope="session")
def consumer_mapping_bucket(s3_client: BaseClient) -> Generator[BucketName]:
    bucket_name = BucketName(os.getenv("CONSUMER_MAPPING_BUCKET_NAME", "test-consumer-mapping-bucket"))
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
    yield bucket_name
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    if "Contents" in response:
        objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
        s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": objects_to_delete})
    s3_client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(scope="session")
def audit_bucket(s3_client: BaseClient) -> Generator[BucketName]:
    bucket_name = BucketName(os.getenv("AUDIT_BUCKET_NAME", "test-audit-bucket"))
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
    yield bucket_name

    # Delete all objects in the bucket before deletion
    objects = s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", [])
    for obj in objects:
        s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
    s3_client.delete_bucket(Bucket=bucket_name)


@pytest.fixture(autouse=True, scope="session")
def firehose_delivery_stream(firehose_client: BaseClient, audit_bucket: BucketName) -> dict[str, Any]:
    return firehose_client.create_delivery_stream(
        DeliveryStreamName="test_kinesis_audit_stream_to_s3",
        DeliveryStreamType="DirectPut",
        ExtendedS3DestinationConfiguration={
            "BucketARN": f"arn:aws:s3:::{audit_bucket}",
            "RoleARN": "arn:aws:iam::000000000000:role/firehose_delivery_role",
            "Prefix": "audit-logs/",
            "BufferingHints": {"SizeInMBs": 1, "IntervalInSeconds": 60},
            "CompressionFormat": "UNCOMPRESSED",
        },
    )


@pytest.fixture(scope="class")
def rsv_campaign_config(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule.IterationFactory.build(
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(type=RuleType.filter),
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
                status_text=None,
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture
def campaign_config_with_rules_having_rule_code(
    s3_client: BaseClient, rules_bucket: BucketName
) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule.IterationFactory.build(
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(
                        type=RuleType.filter, code="Rule Code Excluded postcode In SW19"
                    ),
                    rule.PersonAgeSuppressionRuleFactory.build(code="Rule Code Excluded age less than 75"),
                ],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort1",
                        cohort_group="cohort_group1",
                        positive_description="positive_description",
                        negative_description="negative_description",
                    )
                ],
                status_text=None,
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture
def campaign_config_with_rules_having_rule_mapper(
    s3_client: BaseClient, rules_bucket: BucketName
) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule.IterationFactory.build(
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(
                        type=RuleType.filter, code="Rule Code Excluded postcode In SW19"
                    ),
                    rule.PersonAgeSuppressionRuleFactory.build(
                        name="age_rule_name1", code="Rule Code Excluded age less than 75"
                    ),
                ],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort1",
                        cohort_group="cohort_group1",
                        positive_description="positive_description",
                        negative_description="negative_description",
                    )
                ],
                rules_mapper=RulesMapperFactory.build(
                    root={
                        "OTHER_SETTINGS": RuleEntry(
                            RuleNames=[RuleName("age_rule_name1")],
                            RuleCode=RuleCode("Age rule code from mapper"),
                            RuleText=RuleText("Age Rule Description from mapper"),
                        ),
                        "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=RuleCode(""), RuleText=RuleText("")),
                    }
                ),
                status_text=None,
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture(scope="class")
def inactive_iteration_config(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[list[CampaignConfig]]:
    campaigns, campaign_data_keys = [], []

    target_iteration_dates = {
        "start_date": ("RSV", datetime.date(2025, 1, 1)),  # Active Iteration Date
        "start_date_plus_one_day": ("COVID", datetime.date(2025, 1, 2)),  # Active Iteration Date
        "today": ("FLU", datetime.date(2025, 8, 8)),  # Active Iteration Date
        "tomorrow": ("MMR", datetime.date(2025, 8, 9)),  # Inactive Iteration Date
    }

    for target, data in target_iteration_dates.items():
        campaign = rule.CampaignConfigFactory.build(
            id=f"campaign_{target}",
            target=data[0],
            type="V",
            iterations=[
                rule.IterationFactory.build(
                    iteration_rules=[rule.PersonAgeSuppressionRuleFactory.build()],
                    iteration_cohorts=[rule.IterationCohortFactory.build(cohort_label="cohort_label1")],
                )
            ],
        )

        campaign.start_date = StartDate(datetime.date(2025, 1, 1))
        campaign.end_date = EndDate(datetime.date(2027, 1, 1))
        campaign.iterations[0].iteration_date = data[1]

        campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
        key = f"{campaign.name}.json"
        s3_client.put_object(
            Bucket=rules_bucket, Key=key, Body=json.dumps(campaign_data), ContentType="application/json"
        )
        campaigns.append(campaign)
        campaign_data_keys.append(key)

    yield campaigns

    for key in campaign_data_keys:
        s3_client.delete_object(Bucket=rules_bucket, Key=key)


@pytest.fixture(scope="class")
def campaign_config_with_and_rule(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule.IterationFactory.build(
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(
                        cohort_label="cohort2",
                    ),
                    rule.PersonAgeSuppressionRuleFactory.build(),
                ],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort1",
                        cohort_group="cohort_group1",
                        positive_description="positive_description",
                        negative_description="negative_description",
                    ),
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort2",
                        cohort_group="cohort_group2",
                        positive_description="positive_description",
                        negative_description="negative_description",
                    ),
                ],
                status_text=None,
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture(scope="class")
def campaign_config_with_tokens(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule.IterationFactory.build(
                actions_mapper=rule.ActionsMapperFactory.build(
                    root={
                        "TOKEN_TEST": AvailableAction(
                            ActionType="ButtonAuthLink",
                            ExternalRoutingCode="BookNBS",
                            ActionDescription="## Token - PERSON.POSTCODE: [[PERSON.POSTCODE]].",
                            UrlLabel=(
                                "Token - PERSON.DATE_OF_BIRTH:DATE(%d %B %Y): [[PERSON.DATE_OF_BIRTH:DATE(%d %B %Y)]]."
                            ),
                        ),
                        "TOKEN_TEST2": AvailableAction(
                            ActionType="ButtonAuthLink",
                            ExternalRoutingCode="BookNBS",
                            ActionDescription="## Token - PERSON.GENDER: [[PERSON.GENDER]].",
                            UrlLabel="Token - PERSON.DATE_OF_BIRTH: [[PERSON.DATE_OF_BIRTH]].",
                        ),
                    }
                ),
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(),
                    rule.PersonAgeSuppressionRuleFactory.build(),
                    rule.ICBNonEligibleActionRuleFactory.build(comms_routing="TOKEN_TEST|TOKEN_TEST2"),
                    rule.ICBNonActionableActionRuleFactory.build(comms_routing="TOKEN_TEST"),
                ],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort1",
                        cohort_group="cohort_group1",
                        positive_description="Positive Description",
                        negative_description=(
                            "Token - TARGET.RSV.LAST_SUCCESSFUL_DATE: [[TARGET.RSV.LAST_SUCCESSFUL_DATE]]"
                        ),
                    ),
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort2",
                        cohort_group="cohort_group2",
                        positive_description="Positive Description",
                        negative_description=(
                            "Token - TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y): "
                            "[[TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y)]]"
                        ),
                    ),
                ],
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture(scope="class")
def campaign_config_with_invalid_tokens(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule.IterationFactory.build(
                actions_mapper=rule.ActionsMapperFactory.build(
                    root={
                        "TOKEN_TEST": AvailableAction(
                            ActionType="ButtonAuthLink",
                            ExternalRoutingCode="BookNBS",
                            ActionDescription="## Token - PERSON.ICECREAM: [[PERSON.ICECREAM]].",
                            UrlLabel=(
                                "Token - PERSON.DATE_OF_BIRTH:DATE(%d %B %Y): [[PERSON.DATE_OF_BIRTH:DATE(%d %B %Y)]]."
                            ),
                        )
                    }
                ),
                iteration_rules=[
                    rule.ICBNonEligibleActionRuleFactory.build(comms_routing="TOKEN_TEST"),
                ],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort1",
                        cohort_group="cohort_group1",
                        positive_description="Positive Description",
                        negative_description=(
                            "Token - TARGET.RSV.LAST_SUCCESSFUL_DATE: [[TARGET.RSV.LAST_SUCCESSFUL_DATE]]"
                        ),
                    )
                ],
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture
def campaign_config_with_derived_values(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
    """Campaign config with derived values for testing ADD_DAYS function."""
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="COVID",
        iterations=[
            rule.IterationFactory.build(
                default_comms_routing="DERIVED_VALUES_TEST|DERIVED_VALUES_NEXT_DOSE",
                actions_mapper=rule.ActionsMapperFactory.build(
                    root={
                        "DERIVED_VALUES_TEST": AvailableAction(
                            ActionType="DataValue",
                            ExternalRoutingCode="DateOfLastVaccination",
                            ActionDescription="[[TARGET.COVID.LAST_SUCCESSFUL_DATE]]",
                        ),
                        "DERIVED_VALUES_NEXT_DOSE": AvailableAction(
                            ActionType="DataValue",
                            ExternalRoutingCode="DateOfNextEarliestVaccination",
                            ActionDescription="[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]]",
                        ),
                    }
                ),
                iteration_rules=[],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort_label1",
                        cohort_group="cohort_group1",
                        positive_description="Positive Description",
                        negative_description="Negative Description",
                    )
                ],
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture
def campaign_config_with_derived_values_formatted(
    s3_client: BaseClient, rules_bucket: BucketName
) -> Generator[CampaignConfig]:
    """Campaign config with derived values and date formatting."""
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="COVID",
        iterations=[
            rule.IterationFactory.build(
                default_comms_routing="DERIVED_VALUES_FORMATTED",
                actions_mapper=rule.ActionsMapperFactory.build(
                    root={
                        "DERIVED_VALUES_FORMATTED": AvailableAction(
                            ActionType="DataValue",
                            ExternalRoutingCode="DateOfNextEarliestVaccination",
                            ActionDescription="[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91):DATE(%d %B %Y)]]",
                        ),
                    }
                ),
                iteration_rules=[],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort_label1",
                        cohort_group="cohort_group1",
                        positive_description="Positive Description",
                        negative_description="Negative Description",
                    )
                ],
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture
def campaign_config_with_multiple_add_days(
    s3_client: BaseClient, rules_bucket: BucketName
) -> Generator[CampaignConfig]:
    """Campaign config with multiple actions using ADD_DAYS with different parameters."""
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="COVID",
        iterations=[
            rule.IterationFactory.build(
                default_comms_routing="DERIVED_LAST_DATE|DERIVED_NEXT_DOSE_91|DERIVED_NEXT_DOSE_61",
                actions_mapper=rule.ActionsMapperFactory.build(
                    root={
                        "DERIVED_LAST_DATE": AvailableAction(
                            ActionType="DataValue",
                            ExternalRoutingCode="DateOfLastVaccination",
                            ActionDescription="[[TARGET.COVID.LAST_SUCCESSFUL_DATE]]",
                        ),
                        "DERIVED_NEXT_DOSE_91": AvailableAction(
                            ActionType="DataValue",
                            ExternalRoutingCode="DateOfNextDoseAt91Days",
                            ActionDescription="[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]]",
                        ),
                        "DERIVED_NEXT_DOSE_61": AvailableAction(
                            ActionType="DataValue",
                            ExternalRoutingCode="DateOfNextDoseAt61Days",
                            ActionDescription="[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(61)]]",
                        ),
                    }
                ),
                iteration_rules=[],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort_label1",
                        cohort_group="cohort_group1",
                        positive_description="Positive Description",
                        negative_description="Negative Description",
                    )
                ],
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture
def campaign_config_with_custom_target_attributes(
    s3_client: BaseClient, rules_bucket: BucketName
) -> Generator[CampaignConfig]:
    """Campaign config with custom target attribute names for derived values."""
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="COVID",
        iterations=[
            rule.IterationFactory.build(
                default_comms_routing="CUSTOM_BOOKING_DATE",
                actions_mapper=rule.ActionsMapperFactory.build(
                    root={
                        "CUSTOM_BOOKING_DATE": AvailableAction(
                            ActionType="DataValue",
                            ExternalRoutingCode="NextBookingAvailable",
                            ActionDescription=(
                                "[[TARGET.COVID.NEXT_BOOKING_AVAILABLE:ADD_DAYS(71, LAST_SUCCESSFUL_DATE):"
                                "DATE(%d %B %Y)]]"
                            ),
                        ),
                    }
                ),
                iteration_rules=[],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort_label1",
                        cohort_group="cohort_group1",
                        positive_description="Positive Description",
                        negative_description="Negative Description",
                    )
                ],
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture(scope="class")
def multiple_campaign_configs(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[list[CampaignConfig]]:
    """Create and upload multiple campaign configs to S3, then clean up after tests."""
    campaigns, campaign_data_keys = [], []

    targets = ["RSV", "COVID", "FLU"]
    target_rules_map = {
        targets[0]: [
            rule.PersonAgeSuppressionRuleFactory.build(type=RuleType.filter, description="TOO YOUNG"),
            rule.PostcodeSuppressionRuleFactory.build(type=RuleType.filter, priority=8, cohort_label="cohort_label4"),
        ],
        targets[1]: [
            rule.PersonAgeSuppressionRuleFactory.build(description="TOO YOUNG, your icb is: [[PERSON.ICB]]"),
            rule.PostcodeSuppressionRuleFactory.build(
                priority=12, cohort_label="cohort_label2", description="Your postcode is: [[PERSON.POSTCODE]]"
            ),
        ],
        targets[2]: [rule.ICBRedirectRuleFactory.build()],
    }

    for i in range(3):
        campaign = rule.CampaignConfigFactory.build(
            name=f"campaign_{i}",
            target=targets[i],
            type="V",
            iterations=[
                rule.IterationFactory.build(
                    iteration_rules=target_rules_map.get(targets[i]),
                    iteration_cohorts=[
                        rule.IterationCohortFactory.build(
                            cohort_label=f"cohort_label{i + 1}",
                            cohort_group=f"cohort_group{i + 1}",
                            positive_description=f"positive_desc_{i + 1}",
                            negative_description=f"negative_desc_{i + 1}",
                        ),
                        rule.IterationCohortFactory.build(
                            cohort_label="cohort_label4",
                            cohort_group="cohort_group4",
                            positive_description="positive_desc_4",
                            negative_description="negative_desc_4",
                        ),
                    ],
                    status_text=StatusText(
                        NotEligible=f"You are not eligible to take {targets[i]} vaccines.",
                        NotActionable=f"You have taken {targets[i]} vaccine in the last 90 days",
                        Actionable=f"You can take {targets[i]} vaccine.",
                    ),
                )
            ],
        )
        campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
        key = f"{campaign.name}.json"
        s3_client.put_object(
            Bucket=rules_bucket, Key=key, Body=json.dumps(campaign_data), ContentType="application/json"
        )
        campaigns.append(campaign)
        campaign_data_keys.append(key)

    yield campaigns

    for key in campaign_data_keys:
        s3_client.delete_object(Bucket=rules_bucket, Key=key)


@pytest.fixture(scope="class")
def campaign_config_with_virtual_cohort(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="COVID",
        iterations=[
            rule.IterationFactory.build(
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(type=RuleType.filter),
                    rule.PersonAgeSuppressionRuleFactory.build(),
                ],
                iteration_cohorts=[rule.VirtualCohortFactory.build(cohort_label="virtual_cohort")],
                status_text=None,
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture(scope="class")
def campaign_config_with_missing_descriptions_missing_rule_text(
    s3_client: BaseClient, rules_bucket: BucketName
) -> Generator[CampaignConfig]:
    campaign: CampaignConfig = rule.CampaignConfigFactory.build(
        target="FLU",
        iterations=[
            rule.IterationFactory.build(
                iteration_rules=[
                    rule.PostcodeSuppressionRuleFactory.build(type=RuleType.filter),
                    rule.PersonAgeSuppressionRuleFactory.build(),
                    rule.PersonAgeSuppressionRuleFactory.build(name="Exclude 76 rolling", description=""),
                ],
                iteration_cohorts=[
                    rule.IterationCohortFactory.build(
                        cohort_label="cohort1",
                        cohort_group="cohort_group1",
                        positive_description="",
                        negative_description="",
                    )
                ],
                status_text=None,
            )
        ],
    )
    campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
    s3_client.put_object(
        Bucket=rules_bucket, Key=f"{campaign.name}.json", Body=json.dumps(campaign_data), ContentType="application/json"
    )
    yield campaign
    s3_client.delete_object(Bucket=rules_bucket, Key=f"{campaign.name}.json")


@pytest.fixture
def campaign_configs(request, s3_client: BaseClient, rules_bucket: BucketName) -> Generator[list[CampaignConfig]]:
    """Create and upload multiple campaign configs to S3, then clean up after tests."""
    campaigns, campaign_data_keys = [], []  # noqa: F841

    raw = getattr(
        request, "param", [("RSV", "RSV_campaign_id"), ("COVID", "COVID_campaign_id"), ("FLU", "FLU_campaign_id")]
    )

    targets = []
    campaign_id = []
    status = []

    for t, _id, *rest in raw:
        targets.append(t)
        campaign_id.append(_id)
        status.append(rest[0] if rest else None)

    for i in range(len(targets)):
        campaign: CampaignConfig = rule.CampaignConfigFactory.build(
            name=f"campaign_{i}",
            id=campaign_id[i],
            target=targets[i],
            type="V",
            iterations=[
                rule.IterationFactory.build(
                    iteration_rules=[
                        rule.PostcodeSuppressionRuleFactory.build(type=RuleType.filter),
                        rule.PersonAgeSuppressionRuleFactory.build(),
                        rule.PersonAgeSuppressionRuleFactory.build(name="Exclude 76 rolling", description=""),
                    ],
                    iteration_cohorts=[
                        rule.IterationCohortFactory.build(
                            cohort_label="cohort1",
                            cohort_group="cohort_group1",
                            positive_description="",
                            negative_description="",
                        )
                    ],
                    status_text=None,
                )
            ],
        )

        if status[i] == "inactive":
            campaign.iterations[0].iteration_date = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=7)

        campaign_data = {"CampaignConfig": campaign.model_dump(by_alias=True)}
        key = f"{campaign.name}.json"
        s3_client.put_object(
            Bucket=rules_bucket, Key=key, Body=json.dumps(campaign_data), ContentType="application/json"
        )
        campaign_id.append(campaign)
        campaign_data_keys.append(key)

    yield campaign_id

    for key in campaign_data_keys:
        s3_client.delete_object(Bucket=rules_bucket, Key=key)


@pytest.fixture(scope="class")
def consumer_id() -> ConsumerId:
    return ConsumerId("23-mic7heal-jor6don")


def create_and_put_consumer_mapping_in_s3(
    campaign_config: CampaignConfig, consumer_id: str, consumer_mapping_bucket, s3_client
) -> ConsumerMapping:
    consumer_mapping = ConsumerMapping.model_validate({})
    campaign_entry = ConsumerCampaign(
        CampaignConfigID=campaign_config.id, Description="Test description for campaign mapping"
    )

    consumer_mapping.root[ConsumerId(consumer_id)] = [campaign_entry]
    consumer_mapping_data = consumer_mapping.model_dump(by_alias=True)
    s3_client.put_object(
        Bucket=consumer_mapping_bucket,
        Key="consumer_mapping_config.json",
        Body=json.dumps(consumer_mapping_data),
        ContentType="application/json",
    )
    return consumer_mapping


@pytest.fixture(scope="class")
def consumer_to_active_campaign_having_invalid_tokens_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: BucketName,
    campaign_config_with_invalid_tokens: CampaignConfig,
    consumer_id: ConsumerId,
) -> Generator[ConsumerMapping]:
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_invalid_tokens, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture(scope="class")
def consumer_to_active_campaign_having_tokens_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: BucketName,
    campaign_config_with_tokens: CampaignConfig,
    consumer_id: ConsumerId,
) -> Generator[ConsumerMapping]:
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_tokens, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture(scope="class")
def consumer_to_active_rsv_campaign_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: BucketName,
    rsv_campaign_config: CampaignConfig,
    consumer_id: ConsumerId,
) -> Generator[ConsumerMapping]:
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        rsv_campaign_config, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture(scope="class")
def consumer_to_active_campaign_having_and_rule_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: BucketName,
    campaign_config_with_and_rule: CampaignConfig,
    consumer_id: ConsumerId,
) -> Generator[ConsumerMapping]:
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_and_rule, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_missing_descriptions_and_rule_text_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_missing_descriptions_missing_rule_text: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_missing_descriptions_missing_rule_text, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_having_rules_with_rule_code_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_rules_having_rule_code: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_rules_having_rule_code, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_having_rules_with_rule_mapper_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_rules_having_rule_mapper: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_rules_having_rule_mapper, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_having_only_virtual_cohort_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_virtual_cohort: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_virtual_cohort, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_config_with_derived_values_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_derived_values: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_derived_values, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_config_with_derived_values_formatted_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_derived_values_formatted: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_derived_values_formatted, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_config_with_multiple_add_days_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_multiple_add_days: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_multiple_add_days, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_to_active_campaign_config_with_custom_target_attributes_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    campaign_config_with_custom_target_attributes: CampaignConfig,
    consumer_id: ConsumerId,
):
    consumer_mapping = create_and_put_consumer_mapping_in_s3(
        campaign_config_with_custom_target_attributes, consumer_id, consumer_mapping_bucket, s3_client
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping.json")


@pytest.fixture
def consumer_to_campaign_having_inactive_iteration_mapping(
    s3_client: BaseClient,
    consumer_mapping_bucket: ConsumerMapping,
    inactive_iteration_config: list[CampaignConfig],
    consumer_id: ConsumerId,
):
    mapping = ConsumerMapping.model_validate({})
    mapping.root[consumer_id] = [
        ConsumerCampaign(CampaignConfigID=cc.id, Description=f"Description for {cc.id}")
        for cc in inactive_iteration_config
    ]

    s3_client.put_object(
        Bucket=consumer_mapping_bucket,
        Key="consumer_mapping_config.json",
        Body=json.dumps(mapping.model_dump(by_alias=True)),
        ContentType="application/json",
    )
    yield mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture(scope="class")
def consumer_to_multiple_campaign_configs_mapping(
    multiple_campaign_configs: list[CampaignConfig],
    consumer_id: ConsumerId,
    s3_client: BaseClient,
    consumer_mapping_bucket: BucketName,
) -> Generator[ConsumerMapping]:
    mapping = ConsumerMapping.model_validate({})
    mapping.root[consumer_id] = [
        ConsumerCampaign(CampaignConfigID=cc.id, Description=f"Description for {cc.id}")
        for cc in multiple_campaign_configs
    ]

    s3_client.put_object(
        Bucket=consumer_mapping_bucket,
        Key="consumer_mapping_config.json",
        Body=json.dumps(mapping.model_dump(by_alias=True)),
        ContentType="application/json",
    )
    yield mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


@pytest.fixture
def consumer_mappings(
    request, s3_client: BaseClient, consumer_mapping_bucket: BucketName
) -> Generator[ConsumerMapping]:
    consumer_mapping = ConsumerMapping.model_validate(getattr(request, "param", {}))
    consumer_mapping_data = consumer_mapping.model_dump(by_alias=True)
    s3_client.put_object(
        Bucket=consumer_mapping_bucket,
        Key="consumer_mapping_config.json",
        Body=json.dumps(consumer_mapping_data),
        ContentType="application/json",
    )
    yield consumer_mapping
    s3_client.delete_object(Bucket=consumer_mapping_bucket, Key="consumer_mapping_config.json")


# If you put StubSecretRepo in a separate module, import it instead
class StubSecretRepo(SecretRepo):
    # def __init__(self, current: str = AWS_CURRENT_SECRET, previous: str = AWS_PREVIOUS_SECRET):
    def __init__(self, current: str | None, previous: str | None):
        self._current = current
        self._previous = previous

    def get_secret_current(self, secret_name: str) -> dict[str, str]:  # noqa: ARG002
        if self._current:
            return {"AWSCURRENT": self._current}
        return {}

    def get_secret_previous(self, secret_name: str) -> dict[str, str]:  # noqa: ARG002
        if self._previous:
            return {"AWSPREVIOUS": self._previous}
        return {}


@pytest.fixture
def hashing_service() -> HashingService:
    secret_repo = StubSecretRepo(
        current=AWS_CURRENT_SECRET,
        previous=AWS_PREVIOUS_SECRET,
    )

    # The actual value of the name does not matter for the stub,
    # but we keep it realistic for readability.
    hash_secret_name = HashSecretName("eligibility-signposting-api-dev/hashing_secret")

    return HashingService(
        secret_repo=secret_repo,
        hash_secret_name=hash_secret_name,
    )


@pytest.fixture
def hashing_service_factory() -> Callable[[str | None, str | None], HashingService]:
    def _factory(
        current: str | None = AWS_CURRENT_SECRET, previous: str | None = AWS_PREVIOUS_SECRET
    ) -> HashingService:
        secret_repo = StubSecretRepo(current=current, previous=previous)
        hash_secret_name = HashSecretName("eligibility-signposting-api-dev/hashing_secret")

        return HashingService(
            secret_repo=secret_repo,
            hash_secret_name=hash_secret_name,
        )

    return _factory
