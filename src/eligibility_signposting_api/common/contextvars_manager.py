from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any

from mangum.types import LambdaContext, LambdaEvent

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id_for_logging() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, Any] | None:
            request_id_var.set(context.aws_request_id)
            return func(event, context)

        return wrapper

    return decorator
