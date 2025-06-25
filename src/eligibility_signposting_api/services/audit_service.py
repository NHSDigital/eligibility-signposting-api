from dataclasses import dataclass
from datetime import datetime

from mangum.types import LambdaEvent, LambdaContext


@dataclass
class RequestAuditHeader:
    xRequestID: str
    xCorrelationID: str
    nhsdEndUserOrganisationODS: str


@dataclass
class RequestAuditQueryParams:
    category: str | None
    conditions: str | None
    include_actions: str | None


@dataclass
class RequestAuditData:
    nhs_number: int
    request_timestamp: str
    headers: RequestAuditHeader
    query_params: RequestAuditQueryParams


class AuditService:

    def create_request_audit_data(self, event: LambdaEvent) -> RequestAuditData:
        headers = event.get("headers", {})
        path_params = event.get("pathParameters", {})
        query_params = event.get("queryStringParameters", {})

        request_context = event.get("requestContext", {})
        return RequestAuditData(int(path_params.get("id")),
                                request_context.get("time", datetime.now().strftime("%d/%b/%Y:%H:%M:%S %z")), #TODO: check timestamp format
                                RequestAuditHeader(headers.get("X-Request-ID"),
                                                   headers.get("X-Correlation-ID"),
                                                   headers.get("NHSD-End-User-Organisation-ODS")),
                                RequestAuditQueryParams(query_params.get("category"),
                                                        query_params.get("conditions"),
                                                        query_params.get("include_actions")))
