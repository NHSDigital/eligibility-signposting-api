import logging
import re
from collections.abc import Callable
from functools import wraps

from mangum.types import LambdaContext, LambdaEvent

from eligibility_signposting_api.config.contants import NHS_NUMBER_HEADER

logger = logging.getLogger(__name__)


condition_pattern = re.compile(r"^\s*[a-zA-Z0-9]+\s*$", re.IGNORECASE)
category_pattern = re.compile(r"^\s*(VACCINATIONS|SCREENING|ALL)\s*$", re.IGNORECASE)
include_actions_pattern = re.compile(r"^\s*([YN])\s*$", re.IGNORECASE)


def validate_query_params(query_params: dict[str, str]) -> bool:
    conditions = query_params.get("conditions", "ALL").split(",")
    for condition in conditions:
        search = re.search(condition_pattern, condition)
        if not search:
            logger.error("Invalid condition query param: '%s'", condition)
            return False

    category = query_params.get("category", "ALL")
    if not re.search(category_pattern, category):
        logger.error("Invalid category query param: '%s'", category)
        return False

    include_actions = query_params.get("includeActions", "Y")
    if not re.search(include_actions_pattern, include_actions):
        logger.error("Invalid include actions query param: '%s'", include_actions)
        return False

    return True


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
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, int | str]:
            path_param_nhs_number = event.get("pathParameters", {}).get("id")
            header_nhs_number = event.get("headers", {}).get(NHS_NUMBER_HEADER)

            if not validate_nhs_number(path_param_nhs_number, header_nhs_number):
                return {"statusCode": 403, "body": "NHS number mismatch"}

            query_params_raw = event.get("queryStringParameters")
            if query_params_raw is None:
                query_params = {"category": "ALL", "conditions": "ALL", "includeActions": "Y"}
                event.setdefault("queryStringParameters", query_params)
            else:
                query_params = query_params_raw

            if not validate_query_params(query_params):
                return {"statusCode": 422, "body": "Unprocessable Entity"}

            return func(event, context)

        return wrapper

    return decorator
