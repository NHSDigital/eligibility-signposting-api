import datetime
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
def api_gateway_client(boto3_session: Session, localstack: URL) -> BaseClient:
    return boto3_session.client("apigateway", endpoint_url=str(localstack))


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
def firehose_client(boto3_session: Session, localstack: URL) -> BaseClient:
    return boto3_session.client("firehose", endpoint_url=str(localstack))

@pytest.fixture(scope="session")
def secretsmanager_client(boto3_session: Session, localstack: URL) -> BaseClient:
    """
    Provides a boto3 Secrets Manager client bound to LocalStack.
    Seeds a test secret for use in integration tests.
    """
    client:BaseClient = boto3_session.client(
        service_name="secretsmanager",
        endpoint_url=str(localstack),
        region_name="eu-west-1"
    )

    secret_name = "test_secret"
    secret_value = "test_value_old"

    try:
        client.create_secret(
            Name=secret_name,
            SecretString=secret_value,
        )
    except client.exceptions.ResourceExistsException:
        client.put_secret_value(
            SecretId=secret_name,
            SecretString=secret_value,
        )

    secret_name = "test_secret"
    secret_value = "test_value"

    client.put_secret_value(
        SecretId=secret_name,
        SecretString=secret_value,
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
                    "FIREHOSE_ENDPOINT": os.getenv("LOCALSTACK_INTERNAL_ENDPOINT", "http://localstack:4566/"),
                    "SECRET_MANAGER_ENDPOINT": os.getenv("LOCALSTACK_INTERNAL_ENDPOINT", "http://localstack:4566/"),
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
def configured_api_gateway(api_gateway_client, lambda_client, flask_function: str):
    region = lambda_client.meta.region_name

    api = api_gateway_client.create_rest_api(name="API Gateway Lambda integration")
    rest_api_id = api["id"]

    resources = api_gateway_client.get_resources(restApiId=rest_api_id)
    root_id = next(item["id"] for item in resources["items"] if item["path"] == "/")

    patient_check_res = api_gateway_client.create_resource(
        restApiId=rest_api_id, parentId=root_id, pathPart="patient-check"
    )
    patient_check_id = patient_check_res["id"]

    id_res = api_gateway_client.create_resource(restApiId=rest_api_id, parentId=patient_check_id, pathPart="{id}")
    resource_id = id_res["id"]

    api_gateway_client.put_method(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod="GET",
        authorizationType="NONE",
        requestParameters={"method.request.path.id": True},
    )

    # Integration with actual region
    lambda_uri = (
        f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/"
        f"arn:aws:lambda:{region}:000000000000:function:{flask_function}/invocations"
    )
    api_gateway_client.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod="GET",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=lambda_uri,
        passthroughBehavior="WHEN_NO_MATCH",
    )

    # Permission with matching region
    lambda_client.add_permission(
        FunctionName=flask_function,
        StatementId="apigateway-access",
        Action="lambda:InvokeFunction",
        Principal="apigateway.amazonaws.com",
        SourceArn=f"arn:aws:execute-api:{region}:000000000000:{rest_api_id}/*/GET/patient-check/*",
    )

    # Deploy the API
    api_gateway_client.create_deployment(restApiId=rest_api_id, stageName="dev")

    return {
        "rest_api_id": rest_api_id,
        "resource_id": resource_id,
        "invoke_url": f"http://{rest_api_id}.execute-api.localhost.localstack.cloud:4566/dev/patient-check/{{id}}",
    }


@pytest.fixture
def api_gateway_endpoint(configured_api_gateway: dict) -> URL:
    return URL(f"http://{configured_api_gateway['rest_api_id']}.execute-api.localhost.localstack.cloud:4566/dev")


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
def persisted_person(person_table: Any, faker: Faker) -> Generator[eligibility_status.NHSNumber]:
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
def persisted_77yo_person(person_table: Any, faker: Faker) -> Generator[eligibility_status.NHSNumber]:
    nhs_number = eligibility_status.NHSNumber(faker.nhs_number())
    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=77, maximum_age=77))

    for row in (
        rows := person_rows_builder(
            nhs_number,
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
def persisted_person_all_cohorts(person_table: Any, faker: Faker) -> Generator[eligibility_status.NHSNumber]:
    nhs_number = eligibility_status.NHSNumber(faker.nhs_number())
    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=74, maximum_age=74))

    for row in (
        rows := person_rows_builder(
            nhs_number,
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
def person_with_all_data(person_table: Any, faker: Faker) -> Generator[eligibility_status.NHSNumber]:
    nhs_number = eligibility_status.NHSNumber(faker.nhs_number())
    date_of_birth = eligibility_status.DateOfBirth(datetime.date(1990, 2, 28))

    for row in (
        rows := person_rows_builder(
            nhs_number=nhs_number,
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
def persisted_person_no_cohorts(person_table: Any, faker: Faker) -> Generator[eligibility_status.NHSNumber]:
    nhs_number = eligibility_status.NHSNumber(faker.nhs_number())

    for row in (rows := person_rows_builder(nhs_number).data):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_pc_sw19(person_table: Any, faker: Faker) -> Generator[eligibility_status.NHSNumber]:
    nhs_number = eligibility_status.NHSNumber(
        faker.nhs_number(),
    )
    for row in (rows := person_rows_builder(nhs_number, postcode="SW19", cohorts=["cohort1"]).data):
        person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture
def persisted_person_with_no_person_attribute_type(
    person_table: Any, faker: Faker
) -> Generator[eligibility_status.NHSNumber]:
    nhs_number = eligibility_status.NHSNumber(faker.nhs_number())
    date_of_birth = eligibility_status.DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=65))

    for row in (
        rows := person_rows_builder(nhs_number, date_of_birth=date_of_birth, postcode="hp1", cohorts=["cohort1"]).data
    ):
        if row["ATTRIBUTE_TYPE"] != "PERSON":
            person_table.put_item(Item=row)

    yield nhs_number

    for row in rows:
        person_table.delete_item(Key={"NHS_NUMBER": row["NHS_NUMBER"], "ATTRIBUTE_TYPE": row["ATTRIBUTE_TYPE"]})


@pytest.fixture(scope="session")
def rules_bucket(s3_client: BaseClient) -> Generator[BucketName]:
    bucket_name = BucketName(os.getenv("RULES_BUCKET_NAME", "test-rules-bucket"))
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
    yield bucket_name
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


@pytest.fixture(autouse=True)
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
def campaign_config(s3_client: BaseClient, rules_bucket: BucketName) -> Generator[CampaignConfig]:
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
                rules_mapper={
                    "OTHER_SETTINGS": RuleEntry(
                        RuleNames=[RuleName("age_rule_name1")],
                        RuleCode=RuleCode("Age rule code from mapper"),
                        RuleText=RuleText("Age Rule Description from mapper"),
                    ),
                    "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=RuleCode(""), RuleText=RuleText("")),
                },
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
        campaign.end_date = EndDate(datetime.date(2026, 1, 1))
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
