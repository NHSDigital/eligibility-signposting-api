import json
import logging
import uuid
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from fhir.resources.operationoutcome import OperationOutcome, OperationOutcomeIssue

logger = logging.getLogger(__name__)


class APIErrorResponse:
    def __init__(  # noqa: PLR0913
        self,
        status_code: HTTPStatus,
        fhir_issue_code: str,
        fhir_issue_severity: str,
        fhir_coding_system: str,
        fhir_error_code: str,
        fhir_display_message: str,
    ) -> None:
        self.status_code = status_code
        self.fhir_issue_code = fhir_issue_code
        self.fhir_issue_severity = fhir_issue_severity
        self.fhir_coding_system = fhir_coding_system
        self.fhir_error_code = fhir_error_code
        self.fhir_display_message = fhir_display_message

    def build_operation_outcome_issue(self, diagnostics: str, location: list[str] | None) -> OperationOutcomeIssue:
        details = {
            "coding": [
                {
                    "system": self.fhir_coding_system,
                    "code": self.fhir_error_code,
                    "display": self.fhir_display_message,
                }
            ]
        }
        return OperationOutcomeIssue(
            severity=self.fhir_issue_severity,
            code=self.fhir_issue_code,
            diagnostics=diagnostics,
            location=location,
            details=details,
        )  # pyright: ignore[reportCallIssue]

    def generate_response(self, diagnostics: str, location_param: str | None = None) -> dict[str, Any]:
        issue_location = [f"parameters/{location_param}"] if location_param else None

        problem = OperationOutcome(
            id=str(uuid.uuid4()),
            meta={"lastUpdated": datetime.now(UTC)},
            issue=[self.build_operation_outcome_issue(diagnostics, issue_location)],
        )  # pyright: ignore[reportCallIssue]

        response_body = json.dumps(problem.model_dump(by_alias=True, mode="json"))

        return {
            "statusCode": self.status_code,
            "headers": {"Content-Type": "application/fhir+json"},
            "body": response_body,
        }

    def log_and_generate_response(
        self, log_message: str, diagnostics: str, location_param: str | None = None
    ) -> dict[str, Any]:
        logger.error(log_message)
        return self.generate_response(diagnostics, location_param)


INVALID_INCLUDE_ACTIONS_ERROR = APIErrorResponse(
    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
    fhir_issue_code="value",
    fhir_issue_severity="error",
    fhir_coding_system="https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode",
    fhir_error_code="VALIDATION_ERROR",
    fhir_display_message="The supplied value was not recognised by the API.",
)

INVALID_CATEGORY_ERROR = APIErrorResponse(
    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
    fhir_issue_code="value",
    fhir_issue_severity="error",
    fhir_coding_system="https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode",
    fhir_error_code="VALIDATION_ERROR",
    fhir_display_message="The supplied category was not recognised by the API.",
)

INVALID_CONDITION_FORMAT_ERROR = APIErrorResponse(
    status_code=HTTPStatus.BAD_REQUEST,
    fhir_issue_code="value",
    fhir_issue_severity="error",
    fhir_coding_system="https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode",
    fhir_error_code="VALIDATION_ERROR",
    fhir_display_message="The given conditions were not in the expected format.",
)

NHS_NUMBER_NOT_FOUND_ERROR = APIErrorResponse(
    status_code=HTTPStatus.NOT_FOUND,
    fhir_issue_code="processing",
    fhir_issue_severity="error",
    fhir_coding_system="https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode",
    fhir_error_code="RESOURCE_NOT_FOUND",
    fhir_display_message="The given NHS number was not found in our datasets. "
    "This could be because the number is incorrect or "
    "some other reason we cannot process that number.",
)

INTERNAL_SERVER_ERROR = APIErrorResponse(
    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    fhir_issue_code="unexpected",
    fhir_issue_severity="severe",
    fhir_coding_system="https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode",
    fhir_error_code="UNEXPECTED_ERROR",
    fhir_display_message="An unexpected internal server error occurred.",
)

NHS_NUMBER_MISMATCH_ERROR = APIErrorResponse(
    status_code=HTTPStatus.FORBIDDEN,
    fhir_issue_code="forbidden",
    fhir_issue_severity="error",
    fhir_coding_system="https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode",
    fhir_error_code="NHS_NUMBER_MISMATCH",
    fhir_display_message="The provided NHS number does not match the record.",
)
