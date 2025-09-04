import logging
import traceback

from flask import make_response
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException

from eligibility_signposting_api.common.api_error_response import INTERNAL_SERVER_ERROR

logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> ResponseReturnValue | HTTPException:
    # Let Flask handle its own exceptions for now.
    if isinstance(e, HTTPException):
        return e

    tb = traceback.extract_tb(e.__traceback__)
    stack_only = "".join(traceback.format_list(tb))

    response = INTERNAL_SERVER_ERROR.log_and_generate_response(
        log_message=f"An unexpected error occurred: {stack_only}", diagnostics="An unexpected error occurred."
    )
    return make_response(response.get("body"), response.get("statusCode"), response.get("headers"))
