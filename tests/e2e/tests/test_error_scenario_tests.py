import http

import pytest


@pytest.mark.smoketest
def test_check_for_missing_person(eligibility_client):
    nhs_number = "1234567890"

    request_headers = {"nhs-login-nhs-number": "1234567890"}

    expected_body = {
        "issue": [
            {
                "code": "nhs-number-not-found",
                "diagnostics": f'NHS Number "{nhs_number}" not found.',
                "severity": "information",
            }
        ],
        "resourceType": "OperationOutcome",
    }

    response = eligibility_client.make_request(nhs_number, headers=request_headers, raise_on_error=False)

    assert response["status_code"] == http.HTTPStatus.NOT_FOUND
    assert response["body"] == expected_body


@pytest.mark.smoketest
@pytest.mark.parametrize(
    "test_case",
    [
        {
            "scenario": "correct header - NHS number exists but not found in data",
            "nhs_number": "1234567890",
            "request_headers": {"nhs-login-nhs-number": "1234567890"},
            "expected_status": http.HTTPStatus.NOT_FOUND,
            "expected_body": {
                "issue": [
                    {
                        "code": "nhs-number-not-found",
                        "diagnostics": 'NHS Number "1234567890" not found.',
                        "severity": "information",
                    }
                ],
                "resourceType": "OperationOutcome",
            },
        },
        {
            "scenario": "incorrect header - NHS number mismatch",
            "nhs_number": "1234567890",
            "request_headers": {"nhs-login-nhs-number": "12345678900"},
            "expected_status": http.HTTPStatus.FORBIDDEN,
            "expected_body": "NHS number mismatch",
        },
        {
            "scenario": "missing header - NHS number required",
            "nhs_number": "1234567890",
            "request_headers": {},
            "expected_status": http.HTTPStatus.FORBIDDEN,
            "expected_body": "NHS number mismatch",
        },
    ],
    ids=["correct-header", "incorrect-header", "missing-header"],
)
def test_nhs_login_header_handling(eligibility_client, test_case):
    response = eligibility_client.make_request(
        test_case["nhs_number"],
        headers=test_case["request_headers"],
        raise_on_error=False,
    )

    assert response["status_code"] == test_case["expected_status"], f"{test_case['scenario']} failed on status code"
    assert response["body"] == test_case["expected_body"], f"{test_case['scenario']} failed on response body"
