import logging
import re
from collections.abc import Callable
from functools import wraps

from mangum.types import LambdaContext, LambdaEvent

from eligibility_signposting_api.config.contants import NHS_NUMBER_HEADER

logger = logging.getLogger(__name__)


class MismatchedNHSNumberError(ValueError):
    pass


condition_pattern = re.compile(r"^[a-zA-Z0-9]+$")
category_pattern = re.compile(r"^(VACCINATIONS|SCREENING|ALL)$")
include_actions_pattern = re.compile(r"^([YN])$")


def validate_query_params(params: dict[str, str]) -> bool:
    conditions = params.get("conditions", "ALL").split(",")
    for condition in conditions:
        upper_condition = condition.upper().strip()
        search = re.search(condition_pattern, upper_condition)
        if not search:
            logger.error("Invalid condition query param: '%s'", condition)
            return False

    category = params.get("category", "ALL")
    upper_category = category.upper().strip()
    if not re.search(category_pattern, upper_category):
        logger.error("Invalid category query param: '%s'", category)
        return False

    include_actions = params.get("includeActions", "Y")
    upper_include_actions = include_actions.upper().strip()
    if not re.search(include_actions_pattern, upper_include_actions):
        logger.error("Invalid include_actions query param: '%s'", include_actions)
        return False

    return True


def validate_nhs_number(path_nhs, header_nhs):
    logger.info("NHS numbers from the request", extra={"header_nhs": header_nhs, "path_nhs": path_nhs})
    if header_nhs != path_nhs:
        logger.error("NHS number mismatch", extra={"header_nhs": header_nhs, "path_nhs": path_nhs})
        return False
    return True


def validate_request_params() -> Callable:
    def decorator(func: Callable) -> Callable:  # pragma: no cover
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, int | str]:
            path_param_nhs_number = event.get("pathParameters", {}).get("id")
            header_nhs_number = event.get("headers", {}).get(NHS_NUMBER_HEADER)
            query_params = event.get("queryStringParameters", {})

            if not validate_nhs_number(path_param_nhs_number, header_nhs_number):
                return {"statusCode": 403, "body": "NHS number mismatch"}

            if not validate_query_params(query_params):
                return {"statusCode": 422, "body": "Unprocessable Entity"}

            return func(event, context)

        return wrapper

    return decorator
