import logging
from functools import wraps
from typing import Callable, Any

from mangum.types import LambdaEvent, LambdaContext

logger = logging.getLogger(__name__)

def validate_matching_nhs_number() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> Any:
            headers = event.get("headers", {})
            path_params = event.get("pathParameters", {})

            header_nhs = headers.get("custom-nhs-number-header-name")
            path_nhs = path_params.get("id")

            if header_nhs != path_nhs:
                logger.error("NHS number mismatch",extra={"header_nhs_no":header_nhs, "path_nhs_no": path_nhs})
                raise ValueError(f"NHS number mismatch: header={header_nhs}, path={path_nhs}")
            return func(event, context)
        return wrapper
    return decorator
