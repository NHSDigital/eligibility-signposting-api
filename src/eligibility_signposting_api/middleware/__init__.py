"""Middleware package for the Eligibility Signposting API."""

from eligibility_signposting_api.middleware.security_headers import SecurityHeadersMiddleware

__all__ = ["SecurityHeadersMiddleware"]
