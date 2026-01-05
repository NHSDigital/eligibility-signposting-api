import logging
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from functools import wraps
from typing import Any

from mangum.types import LambdaContext, LambdaEvent
from pythonjsonlogger.json import JsonFormatter

from eligibility_signposting_api.config.config import LOG_LEVEL

request_id_context_var: ContextVar[str | None] = ContextVar("request_id", default=None)

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(module)s.py:%(funcName)s():%(lineno)d %(message)s"


def add_lambda_request_id_to_logger() -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: LambdaEvent, context: LambdaContext) -> dict[str, Any] | None:
            aws_request_id = request_id_context_var.set(context.aws_request_id)
            try:
                return func(event, context)
            finally:
                request_id_context_var.reset(aws_request_id)

        return wrapper

    return decorator


class EnrichedJsonFormatter(JsonFormatter):
    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        log_record["request_id"] = request_id_context_var.get() or "-"
        super().add_fields(log_record, record, message_dict)


def init_logging(quieten: Sequence[str] = ("asyncio", "botocore", "boto3", "mangum", "urllib3")) -> None:
    formatter = EnrichedJsonFormatter(LOG_FORMAT)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.root.handlers = []  # Remove default handlers
    logging.root.setLevel(LOG_LEVEL)
    logging.root.addHandler(handler)

    for q in quieten:
        logging.getLogger(q).setLevel(logging.WARNING)
