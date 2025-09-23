import logging
import re
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import request
from flask.typing import ResponseReturnValue

from eligibility_signposting_api.common.api_error_response import (
    INVALID_CATEGORY_ERROR,
    INVALID_CONDITION_FORMAT_ERROR,
    INVALID_INCLUDE_ACTIONS_ERROR,
    NHS_NUMBER_MISMATCH_ERROR,
)
from eligibility_signposting_api.config.contants import NHS_NUMBER_HEADER

logger = logging.getLogger(__name__)

condition_pattern = re.compile(r"^\s*[a-z0-9]+\s*$", re.IGNORECASE)
category_pattern = re.compile(r"^\s*(VACCINATIONS|SCREENING|ALL)\s*$", re.IGNORECASE)
include_actions_pattern = re.compile(r"^\s*([YN])\s*$", re.IGNORECASE)


def validate_query_params(query_params: dict[str, str]) -> tuple[bool, dict[str, Any] | None]:
    conditions = query_params.get("conditions", "ALL").split(",")
    for condition in conditions:
        search = re.search(condition_pattern, condition)
        if not search:
            return False, get_condition_error_response(condition)

    category = query_params.get("category", "ALL")
    if not re.search(category_pattern, category):
        return False, get_category_error_response(category)

    include_actions = query_params.get("includeActions", "Y")
    if not re.search(include_actions_pattern, include_actions):
        return False, get_include_actions_error_response(include_actions)

    return True, None


def validate_nhs_number(path_nhs: str, header_nhs: str) -> bool:
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
        def wrapper(*args, **kwargs) -> ResponseReturnValue:
            nhs_number = kwargs.get("nhs_number")
            header_nhs_no = request.headers.get(NHS_NUMBER_HEADER)

            if not validate_nhs_number(nhs_number, header_nhs_no):
                message = "You are not authorised to request information for the supplied NHS Number"
                return NHS_NUMBER_MISMATCH_ERROR.log_and_generate_response(log_message=message, diagnostics=message)

            query_params = request.args
            if query_params:
                is_valid, problem = validate_query_params(query_params)
                if not is_valid:
                    return problem

            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_include_actions_error_response(include_actions: str) -> dict[str, Any]:
    diagnostics = f"{include_actions} is not a value that is supported by the API"
    return INVALID_INCLUDE_ACTIONS_ERROR.log_and_generate_response(
        log_message=f"Invalid include actions query param: '{include_actions}'",
        diagnostics=diagnostics,
        location_param="includeActions",
    )


def get_category_error_response(category: str) -> dict[str, Any]:
    diagnostics = f"{category} is not a category that is supported by the API"
    return INVALID_CATEGORY_ERROR.log_and_generate_response(
        log_message=f"Invalid category query param: '{category}'", diagnostics=diagnostics, location_param="category"
    )


def get_condition_error_response(condition: str) -> dict[str, Any]:
    diagnostics = (
        f"{condition} should be a single or comma separated list of condition "
        f"strings with no other punctuation or special characters"
    )
    return INVALID_CONDITION_FORMAT_ERROR.log_and_generate_response(
        log_message=f"Invalid condition query param: '{condition}'",
        diagnostics=diagnostics,
        location_param="conditions",
    )
