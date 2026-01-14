import logging
import os

import wireup.integration.flask
from aws_xray_sdk.core import patch_all
from flask import Flask

from eligibility_signposting_api import audit, repos, services
from eligibility_signposting_api.common.error_handler import handle_exception
from eligibility_signposting_api.config.config import config
from eligibility_signposting_api.config.constants import URL_PREFIX
from eligibility_signposting_api.logging.logs_helper import log_request_trace_metadata
from eligibility_signposting_api.logging.logs_manager import init_logging
from eligibility_signposting_api.logging.tracing_helper import setup_tracing
from eligibility_signposting_api.middleware import SecurityHeadersMiddleware
from eligibility_signposting_api.views import eligibility_blueprint

if os.getenv("ENABLE_XRAY_PATCHING"):
    patch_all()

init_logging()
logger = logging.getLogger(__name__)


def main() -> None:  # pragma: no cover
    """Run the Flask app as a local process."""
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=config()["log_level"] == logging.DEBUG)


def create_app() -> Flask:
    app = Flask(__name__)

    setup_tracing(app)  # Handles X-Ray
    app.before_request(log_request_trace_metadata)

    # Register security headers middleware
    SecurityHeadersMiddleware(app)

    # Register views & error handler
    app.register_blueprint(eligibility_blueprint, url_prefix=f"/{URL_PREFIX}")
    app.register_error_handler(Exception, handle_exception)

    # Set up dependency injection using wireup
    container = wireup.create_sync_container(
        service_modules=[services, repos, audit], parameters={**app.config, **config()}
    )
    wireup.integration.flask.setup(container, app)

    logger.info("app ready", extra={"config": {**app.config, **config()}})
    return app


if __name__ == "__main__":
    main()
