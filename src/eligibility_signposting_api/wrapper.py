import json
import logging
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from http import HTTPStatus
from typing import Any

from mangum.types import LambdaContext, LambdaEvent

from eligibility_signposting_api.config.contants import NHS_NUMBER_HEADER

logger = logging.getLogger(__name__)

condition_pattern = re.compile(r"^\s*[a-zA-Z0-9]+\s*$", re.IGNORECASE)
category_pattern = re.compile(r"^\s*(VACCINATIONS|SCREENING|ALL)\s*$", re.IGNORECASE)
include_actions_pattern = re.compile(r"^\s*([YN])\s*$", re.IGNORECASE)


def validate_query_params(query_params: dict[str, str]) -> tuple[bool, dict[str, Any] | None]:
    conditions = query_params.get("conditions", "ALL").split(",")
    for condition in conditions:
        search = re.search(condition_pattern, condition)
        if not search:
            logger.error("Invalid condition query param: '%s'", condition)
            error_response = get_error_response("conditions", condition)
            logger.error("Error response: %s", error_response)
            return False, error_response

    category = query_params.get("category", "ALL")
    if not re.search(category_pattern, category):
        logger.error("Invalid category query param: '%s'", category)
        error_response = get_error_response("category", category)
        return False, error_response

    include_actions = query_params.get("includeActions", "Y")
    if not re.search(include_actions_pattern, include_actions):
        logger.error("Invalid include actions query param: '%s'", include_actions)
        error_response = get_error_response("value", include_actions)
        return False, error_response

    return True, None


def get_error_response(query_type: str, query_value: str) -> dict[str, Any]:
    operation_outcome = {
        "id": uuid.uuid4(),
        "meta": {
            "lastUpdated": datetime.now(UTC),
        },
        "issue": [
            {
                "severity": "error",
                "code": "value",
                "diagnostics": f"{query_value} is not a {query_type} that is supported by the API",
                "location": [f"parameters/{query_type}"],
                "details": {
                    "coding": [
                        {
                            "system": "https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode",
                            "code": "VALIDATION_ERROR",
                            "display": f"The supplied {query_type} was not recognised by the API.",
                        }
                    ]
                },
            }
        ],
        "resourceType": "OperationOutcome",  # TODO: use real class?
    }
    return {
        "statusCode": HTTPStatus.UNPROCESSABLE_ENTITY,
        "headers": {"Content-Type": "application/fhir+json"},
        "body": json.dumps(operation_outcome, default=str),
    }


def validate_nhs_number(path_nhs: int, header_nhs: int) -> bool:
    logger.info("NHS numbers from the request", extra={"header_nhs": header_nhs, "path_nhs": path_nhs})

    if not header_nhs or not path_nhs:
        logger.error("NHS number is not present", extra={"header_nhs": header_nhs, "path_nhs": path_nhs})
        return False

    if header_nhs != path_nhs:
        logger.error("NHS number mismatch", extra={"header_nhs": header_nhs, "path_nhs": path_nhs})
        return False
    return True


def validate_request_params() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, Any] | None:
            path_param_nhs_number = event.get("pathParameters", {}).get("id")
            header_nhs_number = event.get("headers", {}).get(NHS_NUMBER_HEADER)

            if not validate_nhs_number(path_param_nhs_number, header_nhs_number):
                return {"statusCode": 403, "body": "NHS number mismatch"}

            # TODO: check if this is needed?
            query_params_raw = event.get("queryStringParameters")
            if query_params_raw is None:
                event.setdefault(
                    "queryStringParameters", {"category": "ALL", "conditions": "ALL", "includeActions": "Y"}
                )
            else:
                is_valid, problem = validate_query_params(query_params_raw)
                if not is_valid:
                    return problem

            return func(event, context)

        return wrapper

    return decorator
