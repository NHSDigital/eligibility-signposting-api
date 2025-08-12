from collections.abc import Callable
from functools import wraps
from typing import Any

from aws_xray_sdk.core import xray_recorder
from mangum.types import LambdaContext, LambdaEvent


def tracing_setup() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, Any] | None:
            xray_recorder.begin_subsegment("Lambda")
            try:
                return func(event, context)
            finally:
                xray_recorder.end_subsegment()

        return wrapper

    return decorator
