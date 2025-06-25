import logging
from collections.abc import Callable
from functools import wraps

from mangum.types import LambdaContext, LambdaEvent

from eligibility_signposting_api.config.contants import NHS_NUMBER_HEADER_NAME

logger = logging.getLogger(__name__)


class MismatchedNHSNumberError(ValueError):
    pass


def validate_matching_nhs_number() -> Callable:
    def decorator(func: Callable) -> Callable:  # pragma: no cover
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, int | str]:
            headers = event.get("headers", {})
            path_params = event.get("pathParameters", {})

            header_nhs = headers.get(NHS_NUMBER_HEADER_NAME)
            path_nhs = path_params.get("id")

            logger.info("nhs numbers from the request", extra={"header_nhs": header_nhs, "path_nhs": path_nhs})

            if header_nhs != path_nhs:
                logger.error("NHS number mismatch", extra={"header_nhs_no": header_nhs, "path_nhs_no": path_nhs})
                return {"statusCode": 403, "body": "NHS number mismatch"}
            return func(event, context)

        return wrapper

    return decorator
