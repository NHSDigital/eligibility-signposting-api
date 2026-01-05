"""Tests for security headers middleware."""

from http import HTTPStatus

import pytest
from flask import Flask, make_response
from flask.testing import FlaskClient
from hamcrest import assert_that, contains_string, equal_to, has_entries, is_

from eligibility_signposting_api.middleware import SecurityHeadersMiddleware


class MiddlewareTestError(Exception):
    """Custom exception for middleware error handling tests."""


@pytest.fixture
def test_app() -> Flask:
    """Create a test Flask app with security headers middleware."""
    app = Flask(__name__)
    SecurityHeadersMiddleware(app)

    @app.route("/test")
    def test_route():
        return {"status": "ok"}, HTTPStatus.OK

    @app.route("/error")
    def error_route():
        msg = "Test error"
        raise MiddlewareTestError(msg)

    @app.errorhandler(MiddlewareTestError)
    def handle_value_error(e):
        return {"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

    return app


@pytest.fixture
def client(test_app: Flask) -> FlaskClient:
    """Create a test client."""
    return test_app.test_client()


class TestSecurityHeadersMiddleware:
    """Test suite for SecurityHeadersMiddleware."""

    def test_security_headers_present_on_successful_response(self, client: FlaskClient) -> None:
        """Test that security headers are added to successful responses."""
        response = client.get("/test")

        assert_that(response.status_code, is_(equal_to(HTTPStatus.OK)))
        assert_that(
            dict(response.headers),
            has_entries(
                {
                    "Cache-Control": "no-store, private",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "X-Content-Type-Options": "nosniff",
                }
            ),
        )

    def test_security_headers_present_on_error_response(self, client: FlaskClient) -> None:
        """Test that security headers are added to error responses."""
        response = client.get("/error")

        assert_that(response.status_code, is_(equal_to(HTTPStatus.INTERNAL_SERVER_ERROR)))
        assert_that(
            dict(response.headers),
            has_entries(
                {
                    "Cache-Control": "no-store, private",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "X-Content-Type-Options": "nosniff",
                }
            ),
        )

    def test_security_headers_present_on_404(self, client: FlaskClient) -> None:
        """Test that security headers are added to 404 responses."""
        response = client.get("/nonexistent")

        assert_that(response.status_code, is_(equal_to(HTTPStatus.NOT_FOUND)))
        assert_that(
            dict(response.headers),
            has_entries(
                {
                    "Cache-Control": "no-store, private",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "X-Content-Type-Options": "nosniff",
                }
            ),
        )

    def test_all_expected_headers_are_present(self, client: FlaskClient) -> None:
        """Test that all expected security headers are present."""
        response = client.get("/test")

        expected_headers = {
            "Cache-Control",
            "Strict-Transport-Security",
            "X-Content-Type-Options",
        }

        response_headers = set(response.headers.keys())
        assert expected_headers.issubset(response_headers), (
            f"Missing security headers: {expected_headers - response_headers}"
        )

    def test_cache_control_prevents_caching(self, client: FlaskClient) -> None:
        """Test that Cache-Control header prevents caching of sensitive data."""
        response = client.get("/test")

        cache_control = response.headers.get("Cache-Control")
        assert_that(cache_control, contains_string("no-store"))
        assert_that(cache_control, contains_string("private"))

    def test_hsts_header_enforces_https(self, client: FlaskClient) -> None:
        """Test that HSTS header is properly configured."""
        response = client.get("/test")

        hsts = response.headers.get("Strict-Transport-Security")
        assert_that(hsts, contains_string("max-age=31536000"))
        assert_that(hsts, contains_string("includeSubDomains"))

    def test_content_type_options_prevents_sniffing(self, client: FlaskClient) -> None:
        """Test that X-Content-Type-Options prevents MIME sniffing."""
        response = client.get("/test")

        content_type_options = response.headers.get("X-Content-Type-Options")
        assert_that(content_type_options, is_(equal_to("nosniff")))

    def test_middleware_init_app_method(self) -> None:
        """Test that middleware can be initialized separately using init_app."""
        app = Flask(__name__)
        middleware = SecurityHeadersMiddleware()
        middleware.init_app(app)

        @app.route("/test")
        def test_route():
            return {"status": "ok"}, HTTPStatus.OK

        with app.test_client() as client:
            response = client.get("/test")
            assert_that(response.headers.get("Cache-Control"), is_(equal_to("no-store, private")))

    def test_existing_headers_are_not_overridden(self) -> None:
        """Test that existing headers are not overridden by middleware."""
        app = Flask(__name__)
        SecurityHeadersMiddleware(app)

        @app.route("/test")
        def test_route():
            resp = make_response({"status": "ok"}, HTTPStatus.OK)
            resp.headers["Cache-Control"] = "public, max-age=3600"
            return resp

        with app.test_client() as client:
            response = client.get("/test")
            # Should keep the custom Cache-Control value
            assert_that(response.headers.get("Cache-Control"), is_(equal_to("public, max-age=3600")))
            # But other headers should still be added
            assert_that(response.headers.get("X-Content-Type-Options"), is_(equal_to("nosniff")))
