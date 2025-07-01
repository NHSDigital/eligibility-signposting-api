import http
import pytest


@pytest.mark.smoketest
def test_check_for_missing_person(eligibility_client):
    nhs_number = "1234567890"

    request_headers = {"nhs-login-nhs-number": "1234567890"}

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



@pytest.mark.smoketest
@pytest.mark.parametrize(
    "scenario, nhs_number, request_headers, expected_status, expected_body",
    [
        (
            "correct header - NHS number exists but not found in data",
            "1234567890",
            {"nhs-login-nhs-number": "1234567890"},
            http.HTTPStatus.NOT_FOUND,
            {
                "issue": [{
                    "code": "nhs-number-not-found",
                    "diagnostics": 'NHS Number "1234567890" not found.',
                    "severity": "information"
                }],
                "resourceType": "OperationOutcome"
            },
        ),
        (
            "incorrect header - NHS number mismatch",
            "1234567890",
            {"nhs-login-nhs-number": "12345678900"},
            http.HTTPStatus.FORBIDDEN,
            "NHS number mismatch",
        ),
        (
            "missing header - NHS number required",
            "1234567890",
            {},
            http.HTTPStatus.FORBIDDEN,
            "NHS number mismatch",
        ),
    ],
    ids=[
        "correct-header",
        "incorrect-header",
        "missing-header"
    ]
)
def test_nhs_login_header_handling(
    eligibility_client,
    scenario,
    nhs_number,
    request_headers,
    expected_status,
    expected_body
):
    response = eligibility_client.make_request(
        nhs_number,
        headers=request_headers,
        raise_on_error=False
    )

    response_ststus = response["status_code"]

    assert response["status_code"] == expected_status, f"{scenario} failed on status code"
    assert response["body"] == expected_body, f"{scenario} failed on response body"

