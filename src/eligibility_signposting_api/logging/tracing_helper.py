import logging

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

logger = logging.getLogger(__name__)

#TODO needs manual testing
def setup_tracing(app):
    """Replaces @tracing_setup for Fargate."""
    service_name = 'eligibility-signposting-api'

    # 1. Configure the recorder with the service name
    xray_recorder.configure(service=service_name)

    # 2. Initialize the middleware with only the app and recorder
    XRayMiddleware(app, xray_recorder)
