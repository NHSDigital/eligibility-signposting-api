import logging

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

from eligibility_signposting_api.config.config import config

logger = logging.getLogger(__name__)

#TODO needs manual testing
def setup_tracing(app):
    """xray tracing_setup for Fargate."""
    cfg = config()
    if not cfg.get("enable_xray_patching"):
        return
    service_name = 'eligibility-signposting-api'

    # 1. Configure the recorder with the service name
    xray_recorder.configure(service=service_name)

    # 2. Initialize the middleware with only the app and recorder
    XRayMiddleware(app, xray_recorder)
