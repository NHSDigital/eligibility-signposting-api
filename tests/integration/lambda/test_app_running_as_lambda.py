import base64
import json
import logging
from http import HTTPStatus

import httpx
import stamina
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from brunns.matchers.data import json_matching as is_json_that
from brunns.matchers.response import is_response
from faker import Faker
from hamcrest import assert_that, contains_exactly, contains_string, has_entries, has_item, has_key
from yarl import URL

from eligibility_signposting_api.model.eligibility import NHSNumber
from eligibility_signposting_api.model.rules import CampaignConfig
from eligibility_signposting_api.repos.campaign_repo import BucketName

logger = logging.getLogger(__name__)


def test_install_and_call_lambda_flask(
    lambda_client: BaseClient,
    flask_function: str,
    persisted_person: NHSNumber,
    campaign_config: CampaignConfig,  # noqa: ARG001
):
    """Given lambda installed into localstack, run it via boto3 lambda client"""
    # Given

    # When
    request_payload = {
        "version": "2.0",
        "routeKey": "GET /",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "accept": "application/json",
            "content-type": "application/json",
            "nhs-login-nhs-number": str(persisted_person),
        },
        "pathParameters": {"id": str(persisted_person)},
        "requestContext": {
            "http": {
                "sourceIp": "192.0.0.1",
                "method": "GET",
                "path": f"/patient-check/{persisted_person}",
                "protocol": "HTTP/1.1",
            }
        },
        "queryStringParameters": {},
        "body": None,
        "isBase64Encoded": False,
    }
    response = lambda_client.invoke(
        FunctionName=flask_function,
        InvocationType="RequestResponse",
        Payload=json.dumps(request_payload),
        LogType="Tail",
    )
    log_output = base64.b64decode(response["LogResult"]).decode("utf-8")

    # Then
    assert_that(response, has_entries(StatusCode=HTTPStatus.OK))
    response_payload = json.loads(response["Payload"].read().decode("utf-8"))
    logger.info(response_payload)
    assert_that(
        response_payload,
        has_entries(statusCode=HTTPStatus.OK, body=is_json_that(has_key("processedSuggestions"))),
    )

    assert_that(log_output, contains_string("person_data"))


def test_install_and_call_flask_lambda_over_http(
    persisted_person: NHSNumber,
    campaign_config: CampaignConfig,  # noqa: ARG001
    api_gateway_endpoint: URL,
):
    """Given api-gateway and lambda installed into localstack, run it via http"""
    # Given
    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/{persisted_person}"
    response = httpx.get(
        invoke_url,
        headers={"nhs-login-nhs-number": str(persisted_person)},
        timeout=10,
    )

    # Then
    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_body(is_json_that(has_key("processedSuggestions"))),
    )


def test_install_and_call_flask_lambda_with_unknown_nhs_number(
    flask_function: str,
    campaign_config: CampaignConfig,  # noqa: ARG001
    logs_client: BaseClient,
    api_gateway_endpoint: URL,
    faker: Faker,
):
    """Given lambda installed into localstack, run it via http, with a nonexistent NHS number specified"""
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/{nhs_number}"
    response = httpx.get(
        invoke_url,
        headers={"nhs-login-nhs-number": str(nhs_number)},
        timeout=10,
    )

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.NOT_FOUND)
        .and_body(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="information",
                            code="nhs-number-not-found",
                            diagnostics=f'NHS Number "{nhs_number}" not found.',
                        )
                    ),
                )
            )
        ),
    )

    messages = get_log_messages(flask_function, logs_client)
    assert_that(messages, has_item(contains_string(f"nhs_number '{nhs_number}' not found")))


def get_log_messages(flask_function: str, logs_client: BaseClient) -> list[str]:
    for attempt in stamina.retry_context(on=ClientError, attempts=20, timeout=120):
        with attempt:
            log_streams = logs_client.describe_log_streams(
                logGroupName=f"/aws/lambda/{flask_function}", orderBy="LastEventTime", descending=True
            )
    assert log_streams["logStreams"] != []
    log_stream_name = log_streams["logStreams"][0]["logStreamName"]
    log_events = logs_client.get_log_events(
        logGroupName=f"/aws/lambda/{flask_function}", logStreamName=log_stream_name, limit=100
    )
    return [e["message"] for e in log_events["events"]]


def test_given_nhs_number_in_path_matches_with_nhs_number_in_headers(  # noqa: PLR0913
    lambda_client: BaseClient,  # noqa:ARG001
    persisted_person: NHSNumber,
    campaign_config: CampaignConfig,  # noqa:ARG001
    s3_client: BaseClient,
    audit_bucket: BucketName,
    api_gateway_endpoint: URL,
):
    # Given
    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/{persisted_person}"
    response = httpx.get(
        invoke_url,
        headers={"nhs-login-nhs-number": str(persisted_person)},
        timeout=10,
    )

    # Then
    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_body(is_json_that(has_key("processedSuggestions"))),
    )

    objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
    object_keys = [obj["Key"] for obj in objects]
    latest_key = sorted(object_keys)[-1]
    audit_data = json.loads(s3_client.get_object(Bucket=audit_bucket, Key=latest_key)["Body"].read())
    assert_that(audit_data, has_entries(test_audit="check if audit works"))


def test_given_nhs_number_in_path_does_not_match_with_nhs_number_in_headers_results_in_error_response(
    lambda_client: BaseClient,  # noqa:ARG001
    persisted_person: NHSNumber,
    campaign_config: CampaignConfig,  # noqa:ARG001
    api_gateway_endpoint: URL,
):
    # Given
    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/{persisted_person}"
    response = httpx.get(
        invoke_url,
        headers={"nhs-login-nhs-number": f"123{persisted_person!s}"},
        timeout=10,
    )

    # Then
    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.FORBIDDEN).and_body("NHS number mismatch"),
    )
