import logging
import uuid
from datetime import UTC, datetime
from http import HTTPStatus

from fhir.resources.R4B.operationoutcome import OperationOutcome, OperationOutcomeIssue
from flask import Blueprint, make_response
from flask.typing import ResponseReturnValue
from wireup import Injected

from eligibility_signposting_api.model.eligibility import EligibilityStatus, NHSNumber, Status
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.views.response_models import (
    ConditionName,
    EligibilityResponse,
    LastUpdated,
    Meta,
    ProcessedSuggestion,
    StatusText,
)
from eligibility_signposting_api.views.response_models import Status as ResponseStatus

STATUS_MAPPING = {
    Status.actionable: ResponseStatus.actionable,
    Status.not_actionable: ResponseStatus.not_actionable,
    Status.not_eligible: ResponseStatus.not_eligible,
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
        return make_response(problem.model_dump(by_alias=True), HTTPStatus.NOT_FOUND)
    else:
        eligibility_response = build_eligibility_response(eligibility_status)
        return make_response(eligibility_response.model_dump(by_alias=True), HTTPStatus.OK)


def build_eligibility_response(eligibility_status: EligibilityStatus) -> EligibilityResponse:
    return EligibilityResponse(  # pyright: ignore[reportCallIssue]
        response_id=uuid.uuid4(),  # pyright: ignore[reportCallIssue]
        meta=Meta(last_updated=LastUpdated(datetime.now(tz=UTC))),  # pyright: ignore[reportCallIssue]
        processed_suggestions=[  # pyright: ignore[reportCallIssue]
            ProcessedSuggestion(  # pyright: ignore[reportCallIssue]
                condition_name=ConditionName(condition.condition_name),  # pyright: ignore[reportCallIssue]
                status=STATUS_MAPPING[condition.status],
                status_text=StatusText(f"{condition.status}"),  # pyright: ignore[reportCallIssue]
                eligibility_cohorts=[],  # pyright: ignore[reportCallIssue]
                suitability_rules=[],  # pyright: ignore[reportCallIssue]
                actions=[],
            )
            for condition in eligibility_status.conditions
        ],
    )
