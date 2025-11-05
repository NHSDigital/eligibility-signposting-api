"""Tests for security headers middleware."""

from http import HTTPStatus

import pytest
from flask import Flask
from flask.testing import FlaskClient

from eligibility_signposting_api.middleware import SecurityHeadersMiddleware


class TestError(Exception):
    """Test exception for error handling tests."""


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
        raise TestError(msg)

    @app.errorhandler(TestError)
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

        assert response.status_code == HTTPStatus.OK
        assert response.headers.get("Cache-Control") == "no-store, private"
        assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_security_headers_present_on_error_response(self, client: FlaskClient) -> None:
        """Test that security headers are added to error responses."""
        response = client.get("/error")

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.headers.get("Cache-Control") == "no-store, private"
        assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_security_headers_present_on_404(self, client: FlaskClient) -> None:
        """Test that security headers are added to 404 responses."""
        response = client.get("/nonexistent")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.headers.get("Cache-Control") == "no-store, private"
        assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

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
        assert cache_control is not None
        assert "no-store" in cache_control, "Response should not be stored in any cache"
        assert "private" in cache_control, "Response should be marked as private"

    def test_hsts_header_enforces_https(self, client: FlaskClient) -> None:
        """Test that HSTS header is properly configured."""
        response = client.get("/test")

        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None
        assert "max-age=31536000" in hsts, "HSTS should be valid for 1 year"
        assert "includeSubDomains" in hsts, "HSTS should apply to all subdomains"

    def test_content_type_options_prevents_sniffing(self, client: FlaskClient) -> None:
        """Test that X-Content-Type-Options prevents MIME sniffing."""
        response = client.get("/test")

        content_type_options = response.headers.get("X-Content-Type-Options")
        assert content_type_options == "nosniff", "Should prevent MIME type sniffing"

    def test_middleware_init_app_method(self) -> None:
        """Test that middleware can be initialized separately using init_app."""
        app = Flask(__name__)
        middleware = SecurityHeadersMiddleware()
        middleware.init_app(app)

        @app.route("/test")
        def test_route():
            return {"status": "ok"}, 200

        with app.test_client() as client:
            response = client.get("/test")
            assert response.headers.get("Cache-Control") == "no-store, private"

    def test_existing_headers_are_not_overridden(self) -> None:
        """Test that existing headers are not overridden by middleware."""
        app = Flask(__name__)
        SecurityHeadersMiddleware(app)

        @app.route("/test")
        def test_route():
            from flask import make_response

            resp = make_response({"status": "ok"}, 200)
            resp.headers["Cache-Control"] = "public, max-age=3600"
            return resp

        with app.test_client() as client:
            response = client.get("/test")
            # Should keep the custom Cache-Control value
            assert response.headers.get("Cache-Control") == "public, max-age=3600"
            # But other headers should still be added
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
