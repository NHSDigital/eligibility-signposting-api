import http

import pytest


@pytest.mark.smoketest
def test_check_for_missing_person(eligibility_client):
    nhs_number = "1234567890"

    request_headers = {"authenticated_nhs_number": "1234567890"}

    expected_body = {
        "issue": [{
            "code": "nhs-number-not-found",
            "diagnostics": f'NHS Number "{nhs_number}" not found.',
            "severity": "information"
        }],
        "resourceType": "OperationOutcome"
    }

    response = eligibility_client.make_request(nhs_number, headers=request_headers, raise_on_error=False)

    assert response["status_code"] == http.HTTPStatus.NOT_FOUND
    assert response["body"] == expected_body
