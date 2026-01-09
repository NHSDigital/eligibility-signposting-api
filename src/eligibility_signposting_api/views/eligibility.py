import logging
import os
import uuid
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from flask import Blueprint, make_response, request
from flask.typing import ResponseReturnValue
from wireup import Injected

from eligibility_signposting_api.audit.audit_context import AuditContext
from eligibility_signposting_api.audit.audit_service import AuditService
from eligibility_signposting_api.common.api_error_response import (
    NHS_NUMBER_NOT_FOUND_ERROR,
)
from eligibility_signposting_api.common.request_validator import validate_request_params
from eligibility_signposting_api.config.constants import CONSUMER_ID, URL_PREFIX
from eligibility_signposting_api.model.consumer_mapping import ConsumerId
from eligibility_signposting_api.model.eligibility_status import Condition, EligibilityStatus, NHSNumber, Status
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.views.response_model import eligibility_response
from eligibility_signposting_api.views.response_model.eligibility_response import ProcessedSuggestion

STATUS_MAPPING = {
    Status.actionable: eligibility_response.Status.actionable,
    Status.not_actionable: eligibility_response.Status.not_actionable,
    Status.not_eligible: eligibility_response.Status.not_eligible,
}

logger = logging.getLogger(__name__)

eligibility_blueprint = Blueprint("eligibility", __name__)


@eligibility_blueprint.before_request
def before_request() -> None:
    AuditContext.add_request_details(request)


@eligibility_blueprint.get("/_status")
def api_status() -> ResponseReturnValue:
    return make_response(build_status_payload(), HTTPStatus.OK, {"Content-Type": "application/json"})


@eligibility_blueprint.get("/", defaults={"nhs_number": ""})
@eligibility_blueprint.get("/<nhs_number>")
@validate_request_params()
def check_eligibility(
    nhs_number: NHSNumber, eligibility_service: Injected[EligibilityService], audit_service: Injected[AuditService]
) -> ResponseReturnValue:
    logger.info("checking nhs_number %r in %r", nhs_number, eligibility_service, extra={"nhs_number": nhs_number})

    query_params = _get_or_default_query_params()
    consumer_id = _get_consumer_id_from_headers()

    try:
        eligibility_status = eligibility_service.get_eligibility_status(
            nhs_number,
            query_params["includeActions"],
            query_params["conditions"],
            query_params["category"],
            consumer_id,
        )
    except UnknownPersonError:
        return handle_unknown_person_error(nhs_number)
    else:
        response: eligibility_response.EligibilityResponse = build_eligibility_response(eligibility_status)
        AuditContext.write_to_firehose(audit_service)
        return make_response(response.model_dump(by_alias=True, mode="json", exclude_none=True), HTTPStatus.OK)


def _get_consumer_id_from_headers() -> ConsumerId:
    """
    @validate_request_params() ensures the consumer ID is never null at this stage.
    """
    return ConsumerId(request.headers.get(CONSUMER_ID, ""))


def _get_or_default_query_params() -> dict[str, Any]:
    default_query_params = {"category": "ALL", "conditions": ["ALL"], "includeActions": "Y"}

    if not request.args:
        logger.info("Defaulting all query params as no value was provided, using values %s", default_query_params)
        return default_query_params

    raw_args = request.args.to_dict()
    query_params: dict[str, Any] = {}

    include_actions = raw_args.get("includeActions")
    query_params["includeActions"] = (
        include_actions.upper() if include_actions else default_query_params["includeActions"]
    )
    if include_actions is None:
        logger.info("Defaulting includeActions query param to 'Y' as no value was provided")

    category = raw_args.get("category")
    query_params["category"] = category.upper() if category else default_query_params["category"]
    if category is None:
        logger.info("Defaulting category query param to 'ALL' as no value was provided")

    conditions_str = raw_args.get("conditions")
    if conditions_str:
        query_params["conditions"] = conditions_str.upper().split(",")
    else:
        query_params["conditions"] = default_query_params["conditions"]
        logger.info("Defaulting conditions query param to 'ALL' as no value was provided")

    return query_params


def handle_unknown_person_error(nhs_number: NHSNumber) -> ResponseReturnValue:
    diagnostics = f"NHS Number '{nhs_number}' was not recognised by the Eligibility Signposting API"
    return NHS_NUMBER_NOT_FOUND_ERROR.log_and_generate_response(
        log_message=diagnostics, diagnostics=diagnostics, location_param="id"
    )


def build_eligibility_response(eligibility_status: EligibilityStatus) -> eligibility_response.EligibilityResponse:
    """Return an object representing the API response we are going to send, given an evaluation of the person's
    eligibility."""

    processed_suggestions = []

    for condition in eligibility_status.conditions:
        suggestions = ProcessedSuggestion(  # pyright: ignore[reportCallIssue]
            condition=eligibility_response.ConditionName(condition.condition_name),  # pyright: ignore[reportCallIssue]
            status=STATUS_MAPPING[condition.status],
            statusText=eligibility_response.StatusText(condition.status_text),  # pyright: ignore[reportCallIssue]
            eligibilityCohorts=build_eligibility_cohorts(condition),  # pyright: ignore[reportCallIssue]
            suitabilityRules=build_suitability_results(condition),  # pyright: ignore[reportCallIssue]
            actions=build_actions(condition),
        )

        processed_suggestions.append(suggestions)

    response_id = uuid.uuid4()
    updated = eligibility_response.LastUpdated(datetime.now(tz=UTC))

    AuditContext.add_response_details(response_id, updated)

    return eligibility_response.EligibilityResponse(  # pyright: ignore[reportCallIssue]
        responseId=response_id,  # pyright: ignore[reportCallIssue]
        meta=eligibility_response.Meta(lastUpdated=updated),
        # pyright: ignore[reportCallIssue]
        processedSuggestions=processed_suggestions,
    )


def build_actions(condition: Condition) -> list[eligibility_response.Action] | None:
    if condition.actions is not None:
        return [
            eligibility_response.Action(
                actionType=eligibility_response.ActionType(action.action_type),
                actionCode=eligibility_response.ActionCode(action.action_code),
                description=eligibility_response.Description(action.action_description or ""),
                urlLabel=eligibility_response.UrlLabel(action.url_label or ""),
                urlLink=eligibility_response.UrlLink(str(action.url_link))
                if action.url_link
                else eligibility_response.UrlLink(""),
            )
            for action in condition.actions
        ]

    return None


def build_eligibility_cohorts(condition: Condition) -> list[eligibility_response.EligibilityCohort]:
    """Group Iteration cohorts and make only one entry per cohort group"""

    return [
        eligibility_response.EligibilityCohort(
            cohortCode=eligibility_response.CohortCode(cohort_result.cohort_code),
            cohortText=eligibility_response.CohortText(cohort_result.description),
            cohortStatus=STATUS_MAPPING[cohort_result.status],
        )
        for cohort_result in condition.cohort_results
        if cohort_result and condition.status == cohort_result.status and cohort_result.description
    ]


def build_suitability_results(condition: Condition) -> list[eligibility_response.SuitabilityRule]:
    if condition.status != Status.not_actionable:
        return []

    return [
        eligibility_response.SuitabilityRule(
            ruleType=eligibility_response.RuleType(reason.rule_type.value),
            ruleCode=eligibility_response.RuleCode(reason.rule_code),
            ruleText=eligibility_response.RuleText(reason.rule_text),
        )
        for reason in condition.suitability_rules
        if reason.rule_text
    ]


def build_status_payload() -> dict:
    api_domain_name = os.getenv("API_DOMAIN_NAME", "localhost")
    return {
        "status": "pass",
        "version": "",
        "revision": "",
        "releaseId": "",
        "commitId": "",
        "checks": {
            "healthcheckService:status": [
                {
                    "status": "pass",
                    "timeout": False,
                    "responseCode": HTTPStatus.OK,
                    "outcome": "<html><h1>Ok</h1></html>",
                    "links": {"self": f"https://{api_domain_name}/{URL_PREFIX}/_status"},
                }
            ]
        },
    }
