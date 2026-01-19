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
from freezegun import freeze_time
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_entries,
    has_item,
    has_key,
    is_not,
)
from yarl import URL

from eligibility_signposting_api.model.campaign_config import CampaignConfig
from eligibility_signposting_api.model.eligibility_status import NHSNumber
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

    assert_that(log_output, contains_string("checking nhs_number"))


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
    persisted_person: NHSNumber,
    campaign_config: CampaignConfig,  # noqa: ARG001
    logs_client: BaseClient,
    api_gateway_endpoint: URL,
):
    """Given lambda installed into localstack, run it via http, with a nonexistent NHS number specified"""
    # Given
    nhs_number = f"123{persisted_person}"

    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/{nhs_number}"
    response = httpx.get(
        invoke_url,
        headers={"nhs-login-nhs-number": str(nhs_number)},
        timeout=10,
    )

    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.NOT_FOUND)
        .with_headers(has_entries({"Content-Type": "application/fhir+json"}))
        .and_body(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="error",
                            code="processing",
                            diagnostics=f"NHS Number '{nhs_number!s}' was not "
                            f"recognised by the Eligibility Signposting API",
                            details={
                                "coding": [
                                    {
                                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                        "code": "REFERENCE_NOT_FOUND",
                                        "display": "The given NHS number was not found in our datasets. "
                                        "This could be because the number is incorrect or "
                                        "some other reason we cannot process that number.",
                                    }
                                ]
                            },
                        )
                    ),
                )
            ),
        ),
    )

    messages = get_log_messages(flask_function, logs_client)
    assert_that(
        messages,
        has_item(contains_string(f"NHS Number '{nhs_number}' was not recognised by the Eligibility Signposting API")),
    )


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


def test_given_nhs_number_in_path_matches_with_nhs_number_in_headers_and_check_if_audited(  # noqa: PLR0913
    lambda_client: BaseClient,  # noqa:ARG001
    persisted_person: NHSNumber,
    campaign_config: CampaignConfig,
    s3_client: BaseClient,
    audit_bucket: BucketName,
    api_gateway_endpoint: URL,
    flask_function: str,
    logs_client: BaseClient,
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

    # Then - check if audited
    objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
    object_keys = [obj["Key"] for obj in objects]
    latest_key = sorted(object_keys)[-1]
    audit_data = json.loads(s3_client.get_object(Bucket=audit_bucket, Key=latest_key)["Body"].read())

    expected_headers = {
        "xRequestId": "x_request_id",
        "xCorrelationId": "x_correlation_id",
        "nhsdEndUserOrganisationOds": "nhsd_end_user_organisation_ods",
        "nhsdApplicationId": "nhsd_application_id",
    }
    expected_query_params = {"category": None, "conditions": None, "includeActions": "Y"}

    expected_conditions = [
        {
            "campaignId": campaign_config.id,
            "campaignVersion": campaign_config.version,
            "iterationId": campaign_config.iterations[0].id,
            "iterationVersion": campaign_config.iterations[0].version,
            "conditionName": campaign_config.target,
            "status": "not_actionable",
            "statusText": f"You should have the {campaign_config.target} vaccine",
            "eligibilityCohorts": [{"cohortCode": "cohort1", "cohortStatus": "not_actionable"}],
            "eligibilityCohortGroups": [
                {
                    "cohortCode": "cohort_group1",
                    "cohortText": "positive_description",
                    "cohortStatus": "not_actionable",
                }
            ],
            "filterRules": None,
            "suitabilityRules": [
                {
                    "rulePriority": "10",
                    "ruleName": "Exclude too young less than 75",
                    "ruleMessage": "Exclude too young less than 75",
                }
            ],
            "actionRule": None,
            "actions": [],
        }
    ]

    assert_that(audit_data["request"]["requestTimestamp"], is_not(equal_to("")))
    assert_that(audit_data["request"]["headers"], equal_to(expected_headers))
    assert_that(audit_data["request"]["nhsNumber"], equal_to(persisted_person))
    assert_that(audit_data["request"]["queryParams"], equal_to(expected_query_params))

    assert_that(audit_data["response"]["responseId"], is_not(equal_to("")))
    assert_that(audit_data["response"]["lastUpdated"], is_not(equal_to("")))
    assert_that(audit_data["response"]["condition"], equal_to(expected_conditions))

    messages = get_log_messages(flask_function, logs_client)
    assert_that(
        messages,
        has_item(contains_string("Defaulting category query param to 'ALL' as no value was provided")),
    )
    assert_that(
        messages,
        has_item(contains_string("Defaulting conditions query param to 'ALL' as no value was provided")),
    )


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
        is_response()
        .with_status_code(HTTPStatus.FORBIDDEN)
        .with_headers(has_entries({"Content-Type": "application/fhir+json"}))
        .and_body(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="error",
                            code="forbidden",
                            diagnostics="You are not authorised to request information for the supplied NHS Number",
                            details={
                                "coding": [
                                    {
                                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                        "code": "ACCESS_DENIED",
                                        "display": "Access has been denied to process this request.",
                                    }
                                ]
                            },
                        )
                    ),
                )
            )
        ),
    )


def test_given_nhs_number_not_present_in_headers_results_in_valid_for_application_restricted_users(
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
        timeout=10,
    )

    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_body(is_json_that(has_key("processedSuggestions"))),
    )


def test_given_nhs_number_key_present_in_headers_have_no_value_results_in_error_response(
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
        timeout=10,
    )

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.FORBIDDEN)
        .with_headers(has_entries({"Content-Type": "application/fhir+json", "nhs-login-nhs-number": None}))
        .and_body(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="error",
                            code="forbidden",
                            diagnostics="You are not authorised to request information for the supplied NHS Number",
                            details={
                                "coding": [
                                    {
                                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                        "code": "ACCESS_DENIED",
                                        "display": "Access has been denied to process this request.",
                                    }
                                ]
                            },
                        )
                    ),
                )
            )
        ),
    )


def test_validation_of_query_params_when_all_are_valid(
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
        headers={"nhs-login-nhs-number": persisted_person},
        params={"category": "VACCINATIONS", "conditions": "COVID19", "includeActions": "N"},
        timeout=10,
    )

    # Then
    assert_that(response, is_response().with_status_code(HTTPStatus.OK))


def test_validation_of_query_params_when_invalid_conditions_is_specified(
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
        headers={"nhs-login-nhs-number": persisted_person},
        params={"category": "ALL", "conditions": "23-097"},
        timeout=10,
    )

    # Then
    assert_that(response, is_response().with_status_code(HTTPStatus.BAD_REQUEST))


def test_given_person_has_unique_status_for_different_conditions_with_audit(  # noqa: PLR0913
    lambda_client: BaseClient,  # noqa:ARG001
    persisted_person_all_cohorts: NHSNumber,
    multiple_campaign_configs: list[CampaignConfig],
    s3_client: BaseClient,
    audit_bucket: BucketName,
    api_gateway_endpoint: URL,
):
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
        params={"includeActions": "Y", "category": "VACCINATIONS", "conditions": "COVID,FLU,RSV"},
        timeout=10,
    )

    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_body(is_json_that(has_key("processedSuggestions"))),
    )

    objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
    object_keys = [obj["Key"] for obj in objects]
    latest_key = sorted(object_keys)[-1]
    audit_data = json.loads(s3_client.get_object(Bucket=audit_bucket, Key=latest_key)["Body"].read())

    expected_headers = {
        "xRequestId": "x_request_id",
        "xCorrelationId": "x_correlation_id",
        "nhsdEndUserOrganisationOds": "nhsd_end_user_organisation_ods",
        "nhsdApplicationId": "nhsd_application_id",
    }
    expected_query_params = {"category": "VACCINATIONS", "conditions": "COVID,FLU,RSV", "includeActions": "Y"}

    rsv_campaign = multiple_campaign_configs[0]
    covid_campaign = multiple_campaign_configs[1]
    flu_campaign = multiple_campaign_configs[2]

    expected_conditions = [
        {
            "campaignId": rsv_campaign.id,
            "campaignVersion": rsv_campaign.version,
            "iterationId": rsv_campaign.iterations[0].id,
            "iterationVersion": rsv_campaign.iterations[0].version,
            "conditionName": rsv_campaign.target,
            "status": "not_eligible",
            "statusText": f"You are not eligible to take {rsv_campaign.target} vaccines.",
            "eligibilityCohorts": [
                {"cohortCode": "cohort_label1", "cohortStatus": "not_eligible"},
                {"cohortCode": "cohort_label4", "cohortStatus": "not_eligible"},
            ],
            "eligibilityCohortGroups": [
                {"cohortCode": "cohort_group1", "cohortText": "negative_desc_1", "cohortStatus": "not_eligible"},
                {"cohortCode": "cohort_group4", "cohortText": "negative_desc_4", "cohortStatus": "not_eligible"},
            ],
            "filterRules": [
                {"rulePriority": "10", "ruleName": "Exclude too young less than 75"},
                {"rulePriority": "8", "ruleName": "Excluded postcode In SW19"},
            ],
            "suitabilityRules": None,
            "actionRule": None,
            "actions": [],
        },
        {
            "campaignId": covid_campaign.id,
            "campaignVersion": covid_campaign.version,
            "iterationId": covid_campaign.iterations[0].id,
            "iterationVersion": covid_campaign.iterations[0].version,
            "conditionName": covid_campaign.target,
            "status": "not_actionable",
            "statusText": f"You have taken {covid_campaign.target} vaccine in the last 90 days",
            "eligibilityCohorts": [
                {"cohortCode": "cohort_label2", "cohortStatus": "not_actionable"},
                {"cohortCode": "cohort_label4", "cohortStatus": "not_actionable"},
            ],
            "eligibilityCohortGroups": [
                {"cohortCode": "cohort_group2", "cohortText": "positive_desc_2", "cohortStatus": "not_actionable"},
                {"cohortCode": "cohort_group4", "cohortText": "positive_desc_4", "cohortStatus": "not_actionable"},
            ],
            "filterRules": None,
            "suitabilityRules": [
                {
                    "rulePriority": "10",
                    "ruleName": "Exclude too young less than 75",
                    "ruleMessage": "TOO YOUNG, your icb is: QE1",
                },
                {
                    "rulePriority": "12",
                    "ruleName": "Excluded postcode In SW19",
                    "ruleMessage": "Your postcode is: SW19",
                },
            ],
            "actionRule": None,
            "actions": [],
        },
        {
            "campaignId": flu_campaign.id,
            "campaignVersion": flu_campaign.version,
            "iterationId": flu_campaign.iterations[0].id,
            "iterationVersion": flu_campaign.iterations[0].version,
            "conditionName": flu_campaign.target,
            "status": "actionable",
            "statusText": f"You can take {flu_campaign.target} vaccine.",
            "eligibilityCohorts": [
                {"cohortCode": "cohort_label3", "cohortStatus": "actionable"},
                {"cohortCode": "cohort_label4", "cohortStatus": "actionable"},
            ],
            "eligibilityCohortGroups": [
                {"cohortCode": "cohort_group3", "cohortText": "positive_desc_3", "cohortStatus": "actionable"},
                {"cohortCode": "cohort_group4", "cohortText": "positive_desc_4", "cohortStatus": "actionable"},
            ],
            "filterRules": None,
            "suitabilityRules": None,
            "actionRule": {"rulePriority": "20", "ruleName": "In QE1"},
            "actions": [
                {
                    "internalActionCode": "defaultcomms",
                    "actionType": "defaultcomms",
                    "actionCode": "action_code",
                    "actionDescription": None,
                    "actionUrl": None,
                    "actionUrlLabel": None,
                }
            ],
        },
    ]

    assert_that(audit_data["request"]["requestTimestamp"], is_not(equal_to("")))
    assert_that(audit_data["request"]["headers"], equal_to(expected_headers))
    assert_that(audit_data["request"]["nhsNumber"], equal_to(persisted_person_all_cohorts))
    assert_that(audit_data["request"]["queryParams"], equal_to(expected_query_params))
    assert_that(audit_data["response"]["responseId"], is_not(equal_to("")))
    assert_that(audit_data["response"]["lastUpdated"], is_not(equal_to("")))
    assert_that(audit_data["response"]["condition"], contains_inanyorder(*expected_conditions))


@freeze_time("2025-08-08")
def test_no_active_iteration_returns_empty_processed_suggestions(
    lambda_client: BaseClient,  # noqa:ARG001
    persisted_person_all_cohorts: NHSNumber,
    inactive_iteration_config: list[CampaignConfig],  # noqa:ARG001
    api_gateway_endpoint: URL,
):
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
        params={"includeActions": "Y", "category": "VACCINATIONS", "conditions": "COVID,FLU,RSV"},
        timeout=10,
    )

    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_body(is_json_that(has_key("processedSuggestions"))),
    )

    body = response.json()
    assert_that(
        body["processedSuggestions"],
        contains_inanyorder(
            has_entries("condition", "COVID"),
            has_entries("condition", "RSV"),
            has_entries("condition", "FLU"),
        ),
    )


def test_token_formatting_in_eligibility_response_and_audit(  # noqa: PLR0913
    lambda_client: BaseClient,  # noqa:ARG001
    person_with_all_data: NHSNumber,
    campaign_config_with_tokens: CampaignConfig,  # noqa:ARG001
    s3_client: BaseClient,
    audit_bucket: BucketName,
    api_gateway_endpoint: URL,
    flask_function: str,  # noqa:ARG001
    logs_client: BaseClient,  # noqa:ARG001
):
    invoke_url = f"{api_gateway_endpoint}/patient-check/{person_with_all_data}"
    response = httpx.get(
        invoke_url,
        headers={"nhs-login-nhs-number": str(person_with_all_data)},
        timeout=10,
    )

    assert_that(
        response,
        is_response().with_status_code(HTTPStatus.OK).and_body(is_json_that(has_key("processedSuggestions"))),
    )

    processed_suggestions = response.json()["processedSuggestions"][0]
    response_actions = processed_suggestions["actions"]
    response_eligibility_cohorts = processed_suggestions["eligibilityCohorts"]

    assert response_actions[0]["description"] == "## Token - PERSON.POSTCODE: SW18."
    assert response_actions[0]["urlLabel"] == "Token - PERSON.DATE_OF_BIRTH:DATE(%d %B %Y): 28 February 1990."
    assert response_actions[1]["description"] == "## Token - PERSON.GENDER: 0."
    assert response_actions[1]["urlLabel"] == "Token - PERSON.DATE_OF_BIRTH: 19900228."
    assert response_eligibility_cohorts[0]["cohortText"] == "Token - TARGET.RSV.LAST_SUCCESSFUL_DATE: "
    assert response_eligibility_cohorts[1]["cohortText"] == "Token - TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y): "

    objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
    object_keys = [obj["Key"] for obj in objects]
    latest_key = sorted(object_keys)[-1]
    audit_data = json.loads(s3_client.get_object(Bucket=audit_bucket, Key=latest_key)["Body"].read())

    audit_condition = audit_data["response"]["condition"][0]
    audit_actions = audit_condition["actions"]
    audit_eligibility_cohorts = audit_condition["eligibilityCohortGroups"]

    assert audit_actions[0]["actionDescription"] == "## Token - PERSON.POSTCODE: SW18."
    assert audit_actions[0]["actionUrlLabel"] == "Token - PERSON.DATE_OF_BIRTH:DATE(%d %B %Y): 28 February 1990."
    assert audit_actions[1]["actionDescription"] == "## Token - PERSON.GENDER: 0."
    assert audit_actions[1]["actionUrlLabel"] == "Token - PERSON.DATE_OF_BIRTH: 19900228."
    assert audit_eligibility_cohorts[0]["cohortText"] == "Token - TARGET.RSV.LAST_SUCCESSFUL_DATE: "
    assert audit_eligibility_cohorts[1]["cohortText"] == "Token - TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y): "


def test_incorrect_token_causes_internal_server_error(  # noqa: PLR0913
    lambda_client: BaseClient,  # noqa:ARG001
    person_with_all_data: NHSNumber,
    campaign_config_with_invalid_tokens: CampaignConfig,  # noqa:ARG001
    s3_client: BaseClient,
    audit_bucket: BucketName,
    api_gateway_endpoint: URL,
    flask_function: str,
    logs_client: BaseClient,
):
    invoke_url = f"{api_gateway_endpoint}/patient-check/{person_with_all_data}"
    response = httpx.get(
        invoke_url,
        headers={"nhs-login-nhs-number": str(person_with_all_data)},
        timeout=10,
    )

    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.INTERNAL_SERVER_ERROR)
        .with_headers(has_entries({"Content-Type": "application/fhir+json"}))
        .and_body(
            is_json_that(
                has_entries(
                    resourceType="OperationOutcome",
                    issue=contains_exactly(
                        has_entries(
                            severity="error",
                            code="processing",
                            diagnostics="An unexpected error occurred.",
                            details={
                                "coding": [
                                    {
                                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                        "code": "INTERNAL_SERVER_ERROR",
                                        "display": "An unexpected internal server error occurred.",
                                    }
                                ]
                            },
                        )
                    ),
                )
            ),
        ),
    )

    objects = s3_client.list_objects_v2(Bucket=audit_bucket).get("Contents", [])
    assert len(objects) == 0  # Check there are no audit logs

    assert_that(
        get_log_messages(flask_function, logs_client),
        has_item(contains_string("Invalid attribute name 'ICECREAM' in token '[[PERSON.ICECREAM]]'.")),
    )


def test_status_end_point(api_gateway_endpoint: URL):
    """Given api-gateway and lambda installed into localstack, run it via http"""
    # Given
    # When
    invoke_url = f"{api_gateway_endpoint}/patient-check/_status"
    response = httpx.get(
        invoke_url,
        timeout=10,
    )

    # Then
    assert_that(
        response,
        is_response()
        .with_status_code(HTTPStatus.OK)
        .with_headers(has_entries({"Content-Type": "application/json"}))
        .and_json(
            has_entries(
                {
                    "status": "pass",
                    "checks": has_entries(
                        {
                            "healthcheckService:status": contains_exactly(
                                has_entries(
                                    {
                                        "status": "pass",
                                        "timeout": False,
                                        "responseCode": HTTPStatus.OK,
                                        "outcome": "<html><h1>Ok</h1></html>",
                                        "links": has_entries({"self": "https://localhost/patient-check/_status"}),
                                    }
                                )
                            )
                        }
                    ),
                }
            )
        ),
    )
