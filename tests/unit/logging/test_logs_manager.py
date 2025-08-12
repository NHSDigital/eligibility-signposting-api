import io
import json
import logging
import threading
from http import HTTPStatus
from unittest.mock import MagicMock, Mock

import pytest
from mangum.types import LambdaContext

from eligibility_signposting_api.logging.logs_manager import (
    LOG_FORMAT,
    EnrichedJsonFormatter,
    add_lambda_request_id_to_logger,
    request_id_context_var,
)


def test_decorator_sets_request_id_in_context():
    test_request_id = "test-id-12345"
    mock_context = MagicMock()
    mock_context.aws_request_id = test_request_id

    @add_lambda_request_id_to_logger()
    def decorated_handler(event, context):  # noqa : ARG001
        return request_id_context_var.get()

    result = decorated_handler({}, mock_context)

    assert result == test_request_id


def test_decorator_preserves_function_return_value():
    expected_result = {"statusCode": 200, "body": "Success"}
    mock_context = MagicMock()
    mock_context.aws_request_id = "any-id"

    @add_lambda_request_id_to_logger()
    def decorated_handler(event, context):  # noqa : ARG001
        return expected_result

    result = decorated_handler({}, mock_context)

    assert result == expected_result


def test_request_id_context_is_properly_isolated():
    results = {}

    @add_lambda_request_id_to_logger()
    def decorated_handler(event, context):  # noqa : ARG001
        rid = request_id_context_var.get()
        results[threading.current_thread().name] = rid
        return rid

    def thread_func(name, rid):  # noqa : ARG001
        mock_context = MagicMock(aws_request_id=rid)
        decorated_handler({}, mock_context)

    threads = [
        threading.Thread(target=thread_func, name="Thread-A", args=("Thread-A", "id-A")),
        threading.Thread(target=thread_func, name="Thread-B", args=("Thread-B", "id-B")),
        threading.Thread(target=thread_func, name="Thread-C", args=("Thread-C", "id-C")),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results["Thread-A"] == "id-A"
    assert request_id_context_var.get() is None

    assert results["Thread-B"] == "id-B"
    assert request_id_context_var.get() is None

    assert results["Thread-C"] == "id-C"
    assert request_id_context_var.get() is None


@pytest.fixture
def lambda_context():
    context = Mock(spec=LambdaContext)
    context.aws_request_id = "test-request-id"
    return context


def test_enriched_json_formatter_adds_all_fields(lambda_context):
    @add_lambda_request_id_to_logger()
    def test_handler(event, context):  # noqa : ARG001
        logger = logging.getLogger("test_logger")
        logger.info("Test log inside handler")
        return HTTPStatus.OK

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(EnrichedJsonFormatter(LOG_FORMAT))

    test_logger = logging.getLogger("test_logger")
    test_logger.handlers = []
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)

    result = test_handler({}, lambda_context)
    log_output = log_stream.getvalue()

    test_logger.removeHandler(handler)

    assert result == HTTPStatus.OK
    logged_json = json.loads(log_output)

    assert logged_json["request_id"] == lambda_context.aws_request_id
    assert "asctime" in logged_json
    assert logged_json["levelname"] == "INFO"
    assert logged_json["name"] == "test_logger"
    assert logged_json["module"] == "test_logs_manager"
    assert logged_json["funcName"] == "test_handler"
    assert "lineno" in logged_json
    assert logged_json["message"] == "Test log inside handler"
    assert request_id_context_var.get() is None
