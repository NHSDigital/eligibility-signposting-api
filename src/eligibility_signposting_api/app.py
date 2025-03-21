import logging
from typing import Any

import wireup.integration.flask
from asgiref.wsgi import WsgiToAsgi
from flask import Flask
from mangum import Mangum
from mangum.types import LambdaContext, LambdaEvent

from eligibility_signposting_api import repos, services
from eligibility_signposting_api.config import LOG_LEVEL, config, init_logging
from eligibility_signposting_api.error_handler import handle_exception
from eligibility_signposting_api.views.eligibility import eligibility
from eligibility_signposting_api.views.hello import hello

init_logging()
logger = logging.getLogger(__name__)


def main() -> None:  # pragma: no cover
    """Run the Flask app as a local process."""
    app = create_app()
    app.run(debug=LOG_LEVEL == logging.DEBUG)


def lambda_handler(event: LambdaEvent, context: LambdaContext) -> dict[str, Any]:  # pragma: no cover
    """Run the Flask app as an AWS Lambda."""
    handler = Mangum(WsgiToAsgi(create_app()))
    return handler(event, context)


def create_app() -> Flask:
    app = Flask(__name__)
    logger.info("app created")

    # Register views & error handler
    app.register_blueprint(eligibility, url_prefix="/eligibility")
    app.register_blueprint(hello, url_prefix="/hello")
    app.register_error_handler(Exception, handle_exception)

    # Set up dependency injection using wireup
    container = wireup.create_container(service_modules=[services, repos], parameters=config())
    wireup.integration.flask.setup(container, app, import_flask_config=True)

    logger.info("app ready")
    return app


if __name__ == "__main__":
    main()
