import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from mangum.types import LambdaContext, LambdaEvent

logger = logging.getLogger(__name__)


def log_request_ids() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, Any] | None:
            gateway_request_id = (event.get("requestContext") or {}).get("requestId")
            headers = event.get("headers") or {}
            logger.info(
                "request trace metadata",
                extra={
                    "x_request_id": headers.get("X-Request-ID"),
                    "x_correlation_id": headers.get("X-Correlation-ID"),
                    "gateway_request_id": gateway_request_id,
                },
            )
            return func(event, context)

        return wrapper

    return decorator
