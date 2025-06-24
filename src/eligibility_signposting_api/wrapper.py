import logging
from collections.abc import Callable
from functools import wraps

from mangum.types import LambdaContext, LambdaEvent

logger = logging.getLogger(__name__)


class MismatchedNHSNumberError(ValueError):
    pass


def validate_matching_nhs_number() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, int | str]:
            headers = event.get("headers", {})
            path_params = event.get("pathParameters", {})

            header_nhs = headers.get("custom-nhs-number-header-name")
            path_nhs = path_params.get("id")

            # Fallback: extract from rawPath
            if not path_nhs:
                raw_path = event.get("rawPath", "")
                path_nhs = raw_path.strip("/").split("/")[-1]

            if header_nhs != path_nhs:
                logger.error("NHS number mismatch", extra={"header_nhs_no": header_nhs, "path_nhs_no": path_nhs})
                return {"statusCode": 403, "body": "NHS number mismatch"}
            return func(event, context)

        return wrapper

    return decorator
