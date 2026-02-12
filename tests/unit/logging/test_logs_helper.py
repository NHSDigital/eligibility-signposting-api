import logging

import pytest
from flask import Flask

from eligibility_signposting_api.config.constants import CONSUMER_ID
from eligibility_signposting_api.logging.logs_helper import log_request_trace_metadata


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.before_request(log_request_trace_metadata)

    @app.route("/test-endpoint")
    def test_endpoint():
        return "OK", 200

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.parametrize(
    ("headers", "expected_extra"),
    [
        # 1. Full trace (Standard Fargate/ALB Request)
        (
                {
                    "X-Request-ID": "req-123",
                    "X-Correlation-ID": "corr-abc",
                    "X-Amzn-Trace-Id": "gw-id-999",
                    CONSUMER_ID: "prod-1",
                    "nhsd-application-id": "app-1"
                },
                {
                    "x_request_id": "req-123",
                    "x_correlation_id": "corr-abc",
                    "gateway_request_id": "gw-id-999",
                    "nhse_product_id": "prod-1",
                    "nhsd_application_id": "app-1",
                },
        ),
        # 2. No headers (Function should handle missing keys gracefully)
        (
                {},
                {
                    "x_request_id": None,
                    "x_correlation_id": None,
                    "gateway_request_id": None,
                    "nhse_product_id": None,
                    "nhsd_application_id": None,
                },
        ),
        # 3. Partial/Local trace (No Amazon Trace ID provided) i.e non-Gateway trigger
        (
                {"X-Request-ID": "req-local"},
                {
                    "x_request_id": "req-local",
                    "x_correlation_id": None,
                    "gateway_request_id": None,
                    "nhse_product_id": None,
                    "nhsd_application_id": None,
                },
        ),
    ],
)
def test_log_request_trace_metadata_scenarios(app, headers, expected_extra, caplog):
    with app.test_client() as client:
        with caplog.at_level(logging.INFO):
            client.get("/test", headers=headers)

    record = next((r for r in caplog.records if r.message == "request trace metadata"), None)
    assert record is not None

    for key, val in expected_extra.items():
        assert getattr(record, key) == val
