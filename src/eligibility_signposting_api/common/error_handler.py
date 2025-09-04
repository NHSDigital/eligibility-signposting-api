import logging
import traceback

from flask import make_response
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException

from eligibility_signposting_api.common.api_error_response import INTERNAL_SERVER_ERROR
from eligibility_signposting_api.services.processors.token_processor import TokenError

logger = logging.getLogger(__name__)


def handle_exception(e: Exception) -> ResponseReturnValue | HTTPException:
    if isinstance(e, HTTPException):
        return e

    if isinstance(e, TokenError):
        tb = traceback.extract_tb(e.__traceback__)
        clean_traceback = "".join(traceback.format_list(tb))
        logger.error("A ValueError occurred (value redacted). Traceback follows:\n%s", clean_traceback)
        log_msg = f"An unexpected error occurred: {clean_traceback}"
    else:
        full_traceback = "".join(traceback.format_exception(e))
        logger.exception("Unexpected Exception", exc_info=e)
        log_msg = f"An unexpected error occurred: {full_traceback}"

    response = INTERNAL_SERVER_ERROR.log_and_generate_response(
        log_message=log_msg, diagnostics="An unexpected error occurred."
    )
    return make_response(response.get("body"), response.get("statusCode"), response.get("headers"))
