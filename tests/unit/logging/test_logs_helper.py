import logging
from http import HTTPStatus
from unittest.mock import Mock

import pytest
from mangum.types import LambdaContext


@pytest.fixture
def lambda_context():
    context = Mock(spec=LambdaContext)
    context.aws_request_id = "test-request-id"
    return context


@pytest.mark.parametrize(
    ("headers", "gateway_request_id", "expected_extra"),
    [
        (
            {"X-Request-ID": "req-123", "X-Correlation-ID": "corr-abc"},
            "gw-id-999",
            {
                "x_request_id": "req-123",
                "x_correlation_id": "corr-abc",
                "gateway_request_id": "gw-id-999",
            },
        ),
        (
            {},  # No headers
            "gw-id-000",
            {
                "x_request_id": None,
                "x_correlation_id": None,
                "gateway_request_id": "gw-id-000",
            },
        ),
        (
            {"X-Request-ID": "req-local"},
            None,  # No requestContext (non-Gateway trigger)
            {
                "x_request_id": "req-local",
                "x_correlation_id": None,
                "gateway_request_id": None,
            },
        ),
    ],
)
def test_log_request_ids_decorator_logs_metadata(headers, gateway_request_id, expected_extra, lambda_context, caplog):
    from eligibility_signposting_api.app import log_request_ids_from_headers

    event = {"headers": headers}
    if gateway_request_id is not None:
        event["requestContext"] = {"requestId": gateway_request_id}

    @log_request_ids_from_headers()
    def test_handler(event, context):  # noqa : ARG001
        logger = logging.getLogger("test_logger")
        logger.info("Inside test handler")
        return HTTPStatus.OK

    with caplog.at_level(logging.INFO):
        test_handler(event, lambda_context)

    for record in caplog.records:
        if record.message == "request trace metadata":
            for key, val in expected_extra.items():
                assert getattr(record, key) == val
            break
    else:
        pytest.fail("'request trace metadata' log not found")
