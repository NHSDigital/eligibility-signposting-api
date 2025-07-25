import logging
import os
from typing import Any

import wireup.integration.flask
from asgiref.wsgi import WsgiToAsgi
from aws_xray_sdk.core import patch_all
from flask import Flask
from mangum import Mangum
from mangum.types import LambdaContext, LambdaEvent

from eligibility_signposting_api import audit, repos, services
from eligibility_signposting_api.common.error_handler import handle_exception
from eligibility_signposting_api.common.request_validator import validate_request_params
from eligibility_signposting_api.config.config import config
from eligibility_signposting_api.logging.logs_helper import log_request_ids_from_headers
from eligibility_signposting_api.logging.logs_manager import add_lambda_request_id_to_logger, init_logging
from eligibility_signposting_api.logging.tracing_helper import tracing_setup
from eligibility_signposting_api.views import eligibility_blueprint

if os.getenv("ENABLE_XRAY_PATCHING", "false") == "true":
    patch_all()

init_logging()
logger = logging.getLogger(__name__)


def main() -> None:  # pragma: no cover
    """Run the Flask app as a local process."""
    app = create_app()
    app.run(debug=config()["log_level"] == logging.DEBUG)


@add_lambda_request_id_to_logger()
@tracing_setup()
@log_request_ids_from_headers()
@validate_request_params()
def lambda_handler(event: LambdaEvent, context: LambdaContext) -> dict[str, Any]:  # pragma: no cover
    """Run the Flask app as an AWS Lambda."""
    app = create_app()
    app.debug = config()["log_level"] == logging.DEBUG
    handler = Mangum(WsgiToAsgi(app), lifespan="off")
    handler.config["text_mime_types"].append("application/fhir+json")
    return handler(event, context)


def create_app() -> Flask:
    app = Flask(__name__)
    logger.info("app created")

    # Register views & error handler
    app.register_blueprint(eligibility_blueprint, url_prefix="/patient-check")
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
