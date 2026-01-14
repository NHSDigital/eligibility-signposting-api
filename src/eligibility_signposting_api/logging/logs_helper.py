import logging

from flask import request

logger = logging.getLogger(__name__)

#TODO needs manual testing
def log_request_trace_metadata():
    """Replaces @log_request_ids_from_headers for Fargate."""
    headers = request.headers

    # In Fargate/ALB, X-Amzn-Trace-Id is the standard tracing header
    logger.info(
        "request trace metadata",
        extra={
            "x_request_id": headers.get("X-Request-ID"),
            "x_correlation_id": headers.get("X-Correlation-ID"),
            "gateway_request_id": headers.get("X-Amzn-Trace-Id"),
        },
    )
