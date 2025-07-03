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
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_string,
    equal_to,
    has_entries,
    has_item,
    has_key,
    is_not,
    contains_inanyorder
)
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

def test_given_nhs_number_in_path_matches_with_nhs_number_in_headers_and_return_response(  # noqa: PLR0913
    lambda_client: BaseClient,  # noqa:ARG001
    persisted_person: NHSNumber,
    campaign_config: CampaignConfig,
    s3_client: BaseClient,
    audit_bucket: BucketName,
    api_gateway_endpoint: URL,
):
    # Given
    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/{persisted_person}"
    response = httpx.get(
        invoke_url,
        headers={
            "nhs-login-nhs-number": str(persisted_person),
            "x_request_id": "x_request_id",
            "x_correlation_id": "x_correlation_id",
            "nhsd_end_user_organisation_ods": "nhsd_end_user_organisation_ods",
            "nhsd_application_id": "nhsd_application_id",
        },
        params={"includeActions": "Y"},
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

    expected_headers = {
        "x_request_id": "x_request_id",
        "x_correlation_id": "x_correlation_id",
        "nhsd_end_user_organisation_ods": "nhsd_end_user_organisation_ods",
        "nhsd_application_id": "nhsd_application_id",
    }
    expected_query_params = {"category": None, "conditions": None, "include_actions": "Y"}

    assert_that(audit_data["request"]["request_timestamp"], is_not(equal_to("")))
    assert_that(audit_data["request"]["headers"], equal_to(expected_headers))
    assert_that(audit_data["request"]["nhs_number"], equal_to(persisted_person))
    assert_that(audit_data["request"]["query_params"], equal_to(expected_query_params))

    expected_conditions = [
        {
            "campaign_id": campaign_config.id,
            "campaign_version": campaign_config.version,
            "iteration_id": campaign_config.iterations[0].id,
            "iteration_version": campaign_config.iterations[0].version,
            "condition_name": campaign_config.target,
            "status": "not_actionable",
            "status_text": "not_actionable",
            "eligibility_cohorts": [{"cohort_code": "cohort_group1", "cohort_status": "not_actionable"}],
            "eligibility_cohort_groups": [
                {
                    "cohort_code": "cohort_group1",
                    "cohort_text": "positive_description",
                    "cohort_status": "not_actionable",
                }
            ],
            "filter_rules": None,
            "suitability_rules": {
                "rule_priority": 10,
                "rule_name": "Exclude too young less than 75",
                "rule_message": "Exclude too young less than 75",
            },
            "action_rule": None,
            "actions": [],
        }
    ]

    assert_that(audit_data["response"]["response_id"], is_not(equal_to("")))
    assert_that(audit_data["response"]["last_updated"], is_not(equal_to("")))
    assert_that(audit_data["response"]["condition"], equal_to(expected_conditions))


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

def test_given_person_has_unique_status_for_different_conditions_with_audit(  # noqa: PLR0913
    lambda_client: BaseClient,  # noqa:ARG001
    persisted_person_all_cohorts: NHSNumber,
    multiple_campaign_configs: list[CampaignConfig],
    s3_client: BaseClient,
    audit_bucket: BucketName,
    api_gateway_endpoint: URL,
):
    # Given
    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/{persisted_person_all_cohorts}"
    response = httpx.get(
        invoke_url,
        headers={
            "nhs-login-nhs-number": str(persisted_person_all_cohorts),
            "x_request_id": "x_request_id",
            "x_correlation_id": "x_correlation_id",
            "nhsd_end_user_organisation_ods": "nhsd_end_user_organisation_ods",
            "nhsd_application_id": "nhsd_application_id",
        },
        params={"includeActions": "Y"},
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

    expected_headers = {
        "x_request_id": "x_request_id",
        "x_correlation_id": "x_correlation_id",
        "nhsd_end_user_organisation_ods": "nhsd_end_user_organisation_ods",
        "nhsd_application_id": "nhsd_application_id",
    }
    expected_query_params = {"category": None, "conditions": None, "include_actions": "Y"}

    rsv_campaign = multiple_campaign_configs[0]
    covid_campaign = multiple_campaign_configs[1]
    flu_campaign = multiple_campaign_configs[2]

    expected_conditions = [
        {
            "campaign_id": rsv_campaign.id,
            "campaign_version": rsv_campaign.version,
            "iteration_id": rsv_campaign.iterations[0].id,
            "iteration_version": rsv_campaign.iterations[0].version,
            "condition_name": rsv_campaign.target,
            "status": "not_eligible",
            "status_text": "not_eligible",
            "eligibility_cohorts": [{"cohort_code": "cohort_group1", "cohort_status": "not_eligible"}],
            "eligibility_cohort_groups": [
                {
                    "cohort_code": "cohort_group1",
                    "cohort_text": "negative_desc_1",
                    "cohort_status": "not_eligible",
                }
            ],
            "filter_rules": {
                "rule_priority": 10,
                "rule_name": "Exclude too young less than 75"
            },
            "suitability_rules": None,
            "action_rule": None,
            "actions": [],
        },
        {
            "campaign_id": covid_campaign.id,
            "campaign_version": covid_campaign.version,
            "iteration_id": covid_campaign.iterations[0].id,
            "iteration_version": covid_campaign.iterations[0].version,
            "condition_name": covid_campaign.target,
            "status": "not_actionable",
            "status_text": "not_actionable",
            "eligibility_cohorts": [{"cohort_code": "cohort_group2", "cohort_status": "not_actionable"}],
            "eligibility_cohort_groups": [
                {
                    "cohort_code": "cohort_group2",
                    "cohort_text": "positive_desc_2",
                    "cohort_status": "not_actionable",
                }
            ],
            "filter_rules": None,
            "suitability_rules": {
                "rule_priority": 10,
                "rule_name": "Exclude too young less than 75",
                "rule_message": "Exclude too young less than 75"
            },
            "action_rule": None,
            "actions": [],
        },
        {
            "campaign_id": flu_campaign.id,
            "campaign_version": flu_campaign.version,
            "iteration_id": flu_campaign.iterations[0].id,
            "iteration_version": flu_campaign.iterations[0].version,
            "condition_name": flu_campaign.target,
            "status": "actionable",
            "status_text": "actionable",
            "eligibility_cohorts": [{"cohort_code": "cohort_group3", "cohort_status": "actionable"}],
            "eligibility_cohort_groups": [
                {
                    "cohort_code": "cohort_group3",
                    "cohort_text": "positive_desc_3",
                    "cohort_status": "actionable",
                }
            ],
            "filter_rules": None,
            "suitability_rules": None,
            "action_rule": {
                "rule_priority": 20,
                "rule_name": "In QE1"
            },
            "actions": [{
                "internal_name": None, # TODO: FIX!
                "action_type": "defaultcomms",
                "action_code": "action_code",
                "action_description": None,
                "action_url": None,
                "action_url_label": None
            }],
        }
    ]

    assert_that(audit_data["request"]["request_timestamp"], is_not(equal_to("")))
    assert_that(audit_data["request"]["headers"], equal_to(expected_headers))
    assert_that(audit_data["request"]["nhs_number"], equal_to(persisted_person_all_cohorts))
    assert_that(audit_data["request"]["query_params"], equal_to(expected_query_params))
    assert_that(audit_data["response"]["response_id"], is_not(equal_to("")))
    assert_that(audit_data["response"]["last_updated"], is_not(equal_to("")))
    assert_that(audit_data["response"]["condition"], contains_inanyorder(*expected_conditions))


