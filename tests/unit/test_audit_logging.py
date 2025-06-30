from eligibility_signposting_api.audit_service import RequestAuditData, RequestAuditHeader, \
    RequestAuditQueryParams, AuditService

from mangum.types import LambdaEvent

def test_audit_data_object_populates_response_summary():
    mock_event: LambdaEvent = {
        "pathParameters": {"id": "1112223334"},
        "headers": {
            "X-Request-ID": "request-uuid",
            "X-Correlation-ID": "correlation-uuid",
            "NHSD-End-User-Organisation-ODS": "nhs-ods-code-123"
        },
        "queryStringParameters": {
            "conditions": "RSV",
            "category": "Vaccinations",
            "include_actions": "Y"
        },
        "requestContext": {"time": "01/Jan/2025:00:00:00 +0000"}
    }

    header = RequestAuditHeader(xRequestID="request-uuid", xCorrelationID="correlation-uuid",
                                nhsdEndUserOrganisationODS="nhs-ods-code-123")

    query_params = RequestAuditQueryParams(category="Vaccinations", conditions="RSV", include_actions="Y")

    expected_audit_entry = RequestAuditData(nhs_number=1112223334, request_timestamp="01/Jan/2025:00:00:00 +0000",
                                            headers=header, query_params=query_params)

    audit_service = AuditService()
    actual_audit_entry = audit_service.create_request_audit_data(mock_event)

    assert actual_audit_entry == expected_audit_entry

