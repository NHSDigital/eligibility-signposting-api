import logging
from typing import Any

import wireup.integration.flask
from asgiref.wsgi import WsgiToAsgi
from flask import Flask
from mangum import Mangum
from mangum.types import LambdaContext, LambdaEvent

from eligibility_signposting_api import audit, repos, services
from eligibility_signposting_api.common.contextvars_manager import get_request_id_for_logging
from eligibility_signposting_api.common.error_handler import handle_exception
from eligibility_signposting_api.common.request_validator import validate_request_params
from eligibility_signposting_api.config.config import config, init_logging
from eligibility_signposting_api.views import eligibility_blueprint

init_logging()
logger = logging.getLogger(__name__)


def main() -> None:  # pragma: no cover
    """Run the Flask app as a local process."""
    app = create_app()
    app.run(debug=config()["log_level"] == logging.DEBUG)


@get_request_id_for_logging()
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
