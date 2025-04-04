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
from hamcrest import assert_that, contains_string, has_entries, has_item
from yarl import URL

from eligibility_signposting_api.model.eligibility import DateOfBirth, NHSNumber, Postcode

logger = logging.getLogger(__name__)


def test_install_and_call_lambda_flask(
    lambda_client: BaseClient, flask_function: str, persisted_person: tuple[NHSNumber, DateOfBirth, Postcode]
):
    """Given lambda installed into localstack, run it via boto3 lambda client"""
    # Given
    nhs_number, date_of_birth, postcode = persisted_person

    # When
    request_payload = {
        "version": "2.0",
        "routeKey": "GET /",
        "rawPath": "/eligibility/",
        "rawQueryString": f"nhs_number={nhs_number}",
        "headers": {"accept": "application/json", "content-type": "application/json"},
        "requestContext": {
            "http": {"sourceIp": "192.0.0.1", "method": "GET", "path": "/eligibility/", "protocol": "HTTP/1.1"}
        },
        "queryStringParameters": {"nhs_number": nhs_number},
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
        has_entries(statusCode=HTTPStatus.OK, body=is_json_that(has_entries(processed_suggestions=[]))),
    )

    assert_that(log_output, contains_string("got eligibility_data"))


def test_install_and_call_flask_lambda_over_http(
    flask_function_url: URL, persisted_person: tuple[NHSNumber, DateOfBirth, Postcode]
):
    """Given lambda installed into localstack, run it via http"""
    # Given
    nhs_number, date_of_birth, postcode = persisted_person

    # When
    response = httpx.get(str(flask_function_url / "eligibility" / "" % {"nhs_number": nhs_number}))

    # Then
    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_body(is_json_that(has_entries(processed_suggestions=[]))),
    )


def test_install_and_call_flask_lambda_with_unknown_nhs_number(
    flask_function_url: URL, flask_function: str, logs_client: BaseClient, faker: Faker
):
    """Given lambda installed into localstack, run it via http, with a nonexistent NHS number specified"""
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")

    # When
    response = httpx.get(str(flask_function_url / "eligibility" / "" % {"nhs_number": nhs_number}))

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.NOT_FOUND)
        .and_body(
            is_json_that(
                has_entries(
                    title="nhs_number not found",
                    detail=f"nhs_number {nhs_number} not found.",
                    status=HTTPStatus.NOT_FOUND,
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
