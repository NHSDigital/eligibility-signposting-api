# How to Use the API Error Response Module
This document outlines how to use the `api_error_response.py` module for standardized error handling within the Eligibility Signposting API. The module ensures that all API errors are consistent, logged appropriately, and conform to the FHIR `OperationOutcome` standard.
## Core Concepts
The error handling mechanism is built around the class `APIErrorResponse`.
1. **`APIErrorResponse` Class**: This class is a constructor for a specific type of error. An instance of this class holds configuration for an error, such as the `HTTPStatus`, severity, and various FHIR-specific codes.
2. **Pre-defined Error Instances**: The module defines several singleton instances of for common, application-specific errors. Examples include:
    - `INVALID_CATEGORY_ERROR`
    - `NHS_NUMBER_MISMATCH_ERROR`
    - `INTERNAL_SERVER_ERROR`

3. **`log_and_generate_response()` Method**: This is the primary method to be used. When called on an `APIErrorResponse` instance, it performs two actions:
    - Logs the error with a detailed internal message.
    - Generates a complete HTTP response dictionary (`statusCode`, `headers`, `body`) containing a FHIR-compliant `OperationOutcome` payload.

## How to Use
The primary way to handle errors is to import a pre-defined error object from `api_error_response.py` and call its `log_and_generate_response()` method.
### 1. Handling Specific, Known Errors
For handling validation failures or other expected error conditions, use one of the pre-defined error instances.
The `wrapper.py` module uses this pattern to validate query parameters. If a parameter is invalid, it calls the corresponding error function.
**Example: Invalid "category" parameter**
``` python
# wrapper.py

from eligibility_signposting_api.api_error_response import INVALID_CATEGORY_ERROR

def get_category_error_response(category: str) -> dict[str, Any]:
    """Generates an error response for an invalid category."""

    return INVALID_CATEGORY_ERROR.log_and_generate_response(
        log_message=f"Invalid category query param: '{category}'",
        diagnostics=f"{category} is not a category that is supported by the API",
        location_param="category"
    )
```
**Key Parameters for `log_and_generate_response()`:**
- `log_message`: A detailed message for internal logging. This should contain specific information useful for debugging.
- `diagnostics`: The user-facing error message that will be included in the API response body.
- `location_param` (optional): The name of the parameter that caused the error. This helps pinpoint the issue for API consumers.

### 2. Handling Unexpected Exceptions (Global Error Handler)
For unexpected errors, a global exception handler in `error_handler.py` catches any unhandled exception and returns a generic 500 Internal Server Error. This prevents sensitive information from leaking in stack traces.
``` python
# error_handler.py

from eligibility_signposting_api.api_error_response import INTERNAL_SERVER_ERROR

def handle_exception(e: Exception) -> ResponseReturnValue | HTTPException:
    # Generate a generic, safe response for the client
    response = INTERNAL_SERVER_ERROR.log_and_generate_response(
        log_message=f"An unexpected error occurred: {traceback.format_exception(e)}",
        diagnostics="An unexpected error occurred."
    )
    return make_response(response.get("body"), response.get("statusCode"), response.get("headers"))
```
### 3. Creating New Error Types
If a new, reusable error condition is identified, you should add a new instance of `APIErrorResponse` to `api_error_response.py`
Follow the existing pattern:

``` python
# api_error_response.py

# ... (other error definitions)

SOME_NEW_ERROR = APIErrorResponse(
    status_code=HTTPStatus.BAD_REQUEST,
    fhir_issue_code=FHIRIssueCode.VALUE,
    fhir_issue_severity=FHIRIssueSeverity.ERROR,
    fhir_coding_system=FHIR_SPINE_ERROR_CODE_SYSTEM,
    fhir_error_code=FHIRSpineErrorCode.INVALID_PARAMETER,
    fhir_display_message="A new specific error message for display",
)
```
By centralizing error definitions, we ensure that the API provides a consistent and predictable experience for its consumers.
