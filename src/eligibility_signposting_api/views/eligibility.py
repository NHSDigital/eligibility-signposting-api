import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from http import HTTPStatus

from fhir.resources.R4B.operationoutcome import OperationOutcome, OperationOutcomeIssue
from flask import Blueprint, make_response
from flask.typing import ResponseReturnValue
from wireup import Injected

from eligibility_signposting_api.model.eligibility import Condition, EligibilityStatus, NHSNumber, Status
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.views.response_model import eligibility

STATUS_MAPPING = {
    Status.actionable: eligibility.Status.actionable,
    Status.not_actionable: eligibility.Status.not_actionable,
    Status.not_eligible: eligibility.Status.not_eligible,
}

logger = logging.getLogger(__name__)

eligibility_blueprint = Blueprint("eligibility", __name__)


@eligibility_blueprint.get("/", defaults={"nhs_number": ""})
@eligibility_blueprint.get("/<nhs_number>")
def check_eligibility(nhs_number: NHSNumber, eligibility_service: Injected[EligibilityService]) -> ResponseReturnValue:
    logger.debug("checking nhs_number %r in %r", nhs_number, eligibility_service, extra={"nhs_number": nhs_number})
    try:
        eligibility_status = eligibility_service.get_eligibility_status(nhs_number)
    except UnknownPersonError:
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
    else:
        eligibility_response = build_eligibility_response(eligibility_status)
        return make_response(eligibility_response.model_dump(by_alias=True, mode="json"), HTTPStatus.OK)


def build_eligibility_response(eligibility_status: EligibilityStatus) -> eligibility.EligibilityResponse:
    """Return an object representing the API response we are going to send, given an evaluation of the person's
    eligibility."""

    return eligibility.EligibilityResponse(  # pyright: ignore[reportCallIssue]
        responseId=uuid.uuid4(),  # pyright: ignore[reportCallIssue]
        meta=eligibility.Meta(lastUpdated=eligibility.LastUpdated(datetime.now(tz=UTC))),
        # pyright: ignore[reportCallIssue]
        processedSuggestions=[  # pyright: ignore[reportCallIssue]
            eligibility.ProcessedSuggestion(  # pyright: ignore[reportCallIssue]
                condition=eligibility.ConditionName(condition.condition_name),  # pyright: ignore[reportCallIssue]
                status=STATUS_MAPPING[condition.status],
                statusText=eligibility.StatusText(f"{condition.status}"),  # pyright: ignore[reportCallIssue]
                eligibilityCohorts=build_eligibility_cohorts(condition),  # pyright: ignore[reportCallIssue]
                suitabilityRules=build_suitability_results(condition),  # pyright: ignore[reportCallIssue]
                actions=[],
            )
            for condition in eligibility_status.conditions
        ],
    )


def build_eligibility_cohorts(condition: Condition) -> list[eligibility.EligibilityCohort]:
    """Group Iteration cohorts and make only one entry per cohort group"""

    grouped_cohort_results = defaultdict(list)

    for cohort_result in condition.cohort_results:
        if condition.status == cohort_result.status:
            grouped_cohort_results[cohort_result.cohort_code].append(cohort_result)

    return [
        eligibility.EligibilityCohort(
            cohortCode=cohort_group_code,
            cohortText=cohort_group[0].description,
            cohortStatus=STATUS_MAPPING[cohort_group[0].status],
        )
        for cohort_group_code, cohort_group in grouped_cohort_results.items()
        if cohort_group
    ]


def build_suitability_results(condition: Condition) -> list[eligibility.SuitabilityRule]:
    if condition.status != Status.not_actionable:
        return []

    unique_rule_codes = set()
    suitability_results = []

    for cohort_result in condition.cohort_results:
        if cohort_result.status == Status.not_actionable:
            for reason in cohort_result.reasons:
                if reason.rule_name not in unique_rule_codes:
                    unique_rule_codes.add(reason.rule_name)
                    suitability_results.append(
                        eligibility.SuitabilityRule(
                            ruleType=eligibility.RuleType(reason.rule_type.value),
                            ruleCode=eligibility.RuleCode(reason.rule_name),
                            ruleText=eligibility.RuleText(reason.rule_result),
                        )
                    )

    return suitability_results
