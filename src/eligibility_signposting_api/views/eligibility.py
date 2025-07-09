import logging
import uuid
from datetime import UTC, datetime
from http import HTTPStatus

from fhir.resources.R4B.operationoutcome import OperationOutcome, OperationOutcomeIssue
from flask import Blueprint, make_response, request
from flask.typing import ResponseReturnValue
from wireup import Injected

from eligibility_signposting_api.audit.audit_context import AuditContext
from eligibility_signposting_api.audit.audit_service import AuditService
from eligibility_signposting_api.model.eligibility import Condition, EligibilityStatus, NHSNumber, Status
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.views.response_model import eligibility
from eligibility_signposting_api.views.response_model.eligibility import ProcessedSuggestion

STATUS_MAPPING = {
    Status.actionable: eligibility.Status.actionable,
    Status.not_actionable: eligibility.Status.not_actionable,
    Status.not_eligible: eligibility.Status.not_eligible,
}

logger = logging.getLogger(__name__)

eligibility_blueprint = Blueprint("eligibility", __name__)


@eligibility_blueprint.before_request
def before_request() -> None:
    AuditContext.add_request_details(request)


@eligibility_blueprint.get("/", defaults={"nhs_number": ""})
@eligibility_blueprint.get("/<nhs_number>")
def check_eligibility(
    nhs_number: NHSNumber, eligibility_service: Injected[EligibilityService], audit_service: Injected[AuditService]
) -> ResponseReturnValue:
    logger.info("checking nhs_number %r in %r", nhs_number, eligibility_service, extra={"nhs_number": nhs_number})
    try:
        eligibility_status = eligibility_service.get_eligibility_status(
            nhs_number, include_actions_flag=request.args.get("includeActions") == "Y"
        )
    except UnknownPersonError:
        return handle_unknown_person_error(nhs_number)
    else:
        eligibility_response: eligibility.EligibilityResponse = build_eligibility_response(eligibility_status)
        AuditContext.write_to_firehose(audit_service)
        return make_response(
            eligibility_response.model_dump(by_alias=True, mode="json", exclude_none=True), HTTPStatus.OK
        )


def handle_unknown_person_error(nhs_number: NHSNumber) -> ResponseReturnValue:
    logger.debug("nhs_number %r not found", nhs_number, extra={"nhs_number": nhs_number})
    problem = OperationOutcome(
        issue=[
            OperationOutcomeIssue(
                severity="information",
                code="nhs-number-not-found",
                diagnostics=f'NHS Number "{nhs_number}" not found.',
            )  # pyright: ignore[reportCallIssue]
        ]
    )
    return make_response(problem.model_dump(by_alias=True, mode="json"), HTTPStatus.NOT_FOUND)


def build_eligibility_response(eligibility_status: EligibilityStatus) -> eligibility.EligibilityResponse:
    """Return an object representing the API response we are going to send, given an evaluation of the person's
    eligibility."""

    processed_suggestions = []

    for condition in eligibility_status.conditions:
        suggestions = ProcessedSuggestion(  # pyright: ignore[reportCallIssue]
            condition=eligibility.ConditionName(condition.condition_name),  # pyright: ignore[reportCallIssue]
            status=STATUS_MAPPING[condition.status],
            statusText=eligibility.StatusText(f"{condition.status}"),  # pyright: ignore[reportCallIssue]
            eligibilityCohorts=build_eligibility_cohorts(condition),  # pyright: ignore[reportCallIssue]
            suitabilityRules=build_suitability_results(condition),  # pyright: ignore[reportCallIssue]
            actions=build_actions(condition),
        )

        processed_suggestions.append(suggestions)

    response_id = uuid.uuid4()
    updated = eligibility.LastUpdated(datetime.now(tz=UTC))

    AuditContext.add_response_details(response_id, updated)

    return eligibility.EligibilityResponse(  # pyright: ignore[reportCallIssue]
        responseId=response_id,  # pyright: ignore[reportCallIssue]
        meta=eligibility.Meta(lastUpdated=updated),
        # pyright: ignore[reportCallIssue]
        processedSuggestions=processed_suggestions,
    )


def build_actions(condition: Condition) -> list[eligibility.Action] | None:
    if condition.actions is not None:
        return [
            eligibility.Action(
                actionType=eligibility.ActionType(action.action_type),
                actionCode=eligibility.ActionCode(action.action_code),
                description=eligibility.Description(action.action_description or ""),
                urlLabel=eligibility.UrlLabel(action.url_label or ""),
                urlLink=eligibility.UrlLink(str(action.url_link)) if action.url_link else eligibility.UrlLink(""),
            )
            for action in condition.actions
        ]

    return None


def build_eligibility_cohorts(condition: Condition) -> list[eligibility.EligibilityCohort]:
    """Group Iteration cohorts and make only one entry per cohort group"""

    return [
        eligibility.EligibilityCohort(
            cohortCode=eligibility.CohortCode(cohort_result.cohort_code),
            cohortText=eligibility.CohortText(cohort_result.description),
            cohortStatus=STATUS_MAPPING[cohort_result.status],
        )
        for cohort_result in condition.cohort_results
        if cohort_result and condition.status == cohort_result.status and cohort_result.description
    ]


def build_suitability_results(condition: Condition) -> list[eligibility.SuitabilityRule]:
    """Make only one entry if there are duplicate rules"""
    if condition.status != Status.not_actionable:
        return []

    unique_rule_codes = set()
    suitability_results = []

    for cohort_result in condition.cohort_results:
        if cohort_result.status == Status.not_actionable:
            for reason in cohort_result.reasons:
                if reason.rule_name not in unique_rule_codes and reason.rule_description:
                    unique_rule_codes.add(reason.rule_name)
                    suitability_results.append(
                        eligibility.SuitabilityRule(
                            ruleType=eligibility.RuleType(reason.rule_type.value),
                            ruleCode=eligibility.RuleCode(reason.rule_name),
                            ruleText=eligibility.RuleText(reason.rule_description),
                        )
                    )

    return suitability_results
