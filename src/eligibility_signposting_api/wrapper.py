import logging
from functools import wraps
from typing import Callable, Any

from mangum.types import LambdaEvent, LambdaContext

logger = logging.getLogger(__name__)

class MismatchedNHSNumberError(ValueError):
    pass

def validate_matching_nhs_number() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> Any:
            logger.info("############### Validating NHS number")
            headers = event.get("headers", {})
            path_params = event.get("pathParameters", {})

            header_nhs = headers.get("custom-nhs-number-header-name")

            path_nhs = path_params.get("id")

            # Fallback: extract from rawPath
            if not path_nhs:
                raw_path = event.get("rawPath", "")
                path_nhs = raw_path.strip("/").split("/")[-1]

            logger.info(f"nhs_path_{path_nhs}")
            logger.info(f"nhs_header_{header_nhs}")

            if header_nhs != path_nhs:
                logger.error("NHS number mismatch", extra={
                    "header_nhs_no": header_nhs,
                    "path_nhs_no": path_nhs
                })
                raise MismatchedNHSNumberError(f"NHS number mismatch: header={header_nhs}, path={path_nhs}")
            return func(event, context)
        return wrapper
    return decorator
