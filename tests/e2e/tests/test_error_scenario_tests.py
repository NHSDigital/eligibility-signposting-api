import http

import pytest

from tests.e2e.utils.s3_config_manager import delete_all_configs_from_s3


@pytest.mark.errorscenarios
@pytest.mark.smoketest
def test_check_for_missing_person(eligibility_client):
    nhs_number = "9934567890"

    request_headers = {"nhs-login-nhs-number": "9934567890"}

    expected_body = {
        "resourceType": "OperationOutcome",
        "id": "<ignored>",
        "meta": {"lastUpdated": "<ignored>"},
        "issue": [
            {
                "severity": "error",
                "code": "processing",
                "details": {
                    "coding": [
                        {
                            "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                            "code": "REFERENCE_NOT_FOUND",
                            "display": "The given NHS number was not found in our datasets. "
                            "This could be because the number is incorrect or some other reason "
                            "we cannot process that number.",
                        }
                    ]
                },
                "diagnostics": "NHS Number '9934567890' was not recognised by the Eligibility Signposting API",
                "location": ["parameters/id"],
            }
        ],
    }

    response = eligibility_client.make_request(nhs_number, headers=request_headers, raise_on_error=False)

    assert response["status_code"] == http.HTTPStatus.NOT_FOUND
    assert response["body"] == expected_body
    assert response["headers"].get("Content-Type".lower()) == "application/fhir+json"


@pytest.mark.errorscenarios
@pytest.mark.parametrize(
    "test_case",
    [
        {
            "scenario": "correct header - NHS number exists but not found in data",
            "nhs_number": "9934567890",
            "request_headers": {"nhs-login-nhs-number": "9934567890"},
            "expected_status": http.HTTPStatus.NOT_FOUND,
            "expected_body": {
                "resourceType": "OperationOutcome",
                "id": "<ignored>",
                "meta": {"lastUpdated": "<ignored>"},
                "issue": [
                    {
                        "severity": "error",
                        "code": "processing",
                        "details": {
                            "coding": [
                                {
                                    "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                    "code": "REFERENCE_NOT_FOUND",
                                    "display": "The given NHS number was not found in our datasets. "
                                    "This could be because the number is incorrect or some other reason we "
                                    "cannot process that number.",
                                }
                            ]
                        },
                        "diagnostics": "NHS Number '9934567890' was not recognised by the Eligibility Signposting API",
                        "location": ["parameters/id"],
                    }
                ],
            },
        },
        {
            "scenario": "incorrect header - NHS number mismatch",
            "nhs_number": "9934567890",
            "request_headers": {"nhs-login-nhs-number": "99345678900"},
            "expected_status": http.HTTPStatus.FORBIDDEN,
            "expected_body": {
                "resourceType": "OperationOutcome",
                "id": "<ignored>",
                "meta": {"lastUpdated": "<ignored>"},
                "issue": [
                    {
                        "severity": "error",
                        "code": "forbidden",
                        "details": {
                            "coding": [
                                {
                                    "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                    "code": "INVALID_NHS_NUMBER",
                                    "display": "The provided NHS number does not match the record.",
                                }
                            ]
                        },
                        "diagnostics": "NHS Number 9934567890 does not match the header NHS Number 99345678900",
                        "location": ["parameters/id"],
                    }
                ],
            },
        },
        {
            "scenario": "missing header - NHS number required",
            "nhs_number": "1234567890",
            "request_headers": {},
            "expected_status": http.HTTPStatus.FORBIDDEN,
            "expected_body": {
                "resourceType": "OperationOutcome",
                "id": "<ignored>",
                "meta": {"lastUpdated": "<ignored>"},
                "issue": [
                    {
                        "severity": "error",
                        "code": "forbidden",
                        "details": {
                            "coding": [
                                {
                                    "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                    "code": "INVALID_NHS_NUMBER",
                                    "display": "The provided NHS number does not match the record.",
                                }
                            ]
                        },
                        "diagnostics": "NHS Number 1234567890 does not match the header NHS Number ",
                        "location": ["parameters/id"],
                    }
                ],
            },
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
    assert response["headers"].get("Content-Type".lower()) == "application/fhir+json"


@pytest.mark.errorscenarios
@pytest.mark.parametrize(
    "test_case",
    [
        {
            "scenario": "invalid conditions - use special character in conditions",
            "nhs_number": "9990032010",
            "request_headers": {"nhs-login-nhs-number": "9990032010"},
            "query_params": {"conditions": "covid-rsv"},
            "expected_status": http.HTTPStatus.BAD_REQUEST,
            "expected_body": {
                "id": "<ignored>",
                "issue": [
                    {
                        "code": "value",
                        "details": {
                            "coding": [
                                {
                                    "code": "INVALID_PARAMETER",
                                    "display": "The given conditions were not in the expected format.",
                                    "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                }
                            ]
                        },
                        "diagnostics": "covid-rsv should be a single or comma separated list of condition strings "
                        "with no other punctuation or special characters",
                        "location": ["parameters/conditions"],
                        "severity": "error",
                    }
                ],
                "meta": {"lastUpdated": "<ignored>"},
                "resourceType": "OperationOutcome",
            },
        },
        {
            "scenario": "unknown-category - misspelt category",
            "nhs_number": "9990032010",
            "request_headers": {"nhs-login-nhs-number": "9990032010"},
            "query_params": {"category": "VACCINATIONSS"},
            "expected_status": http.HTTPStatus.UNPROCESSABLE_ENTITY,
            "expected_body": {
                "id": "<ignored>",
                "issue": [
                    {
                        "code": "value",
                        "details": {
                            "coding": [
                                {
                                    "code": "INVALID_PARAMETER",
                                    "display": "The supplied category was not recognised by the API.",
                                    "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                                }
                            ]
                        },
                        "diagnostics": "VACCINATIONSS is not a category that is supported by the API",
                        "location": ["parameters/category"],
                        "severity": "error",
                    }
                ],
                "meta": {"lastUpdated": "<ignored>"},
                "resourceType": "OperationOutcome",
            },
        },
    ],
    ids=["invalid-conditions", "unknown-category"],
)
def test_query_param_errors(eligibility_client, test_case):
    response = eligibility_client.make_request(
        test_case["nhs_number"],
        headers=test_case["request_headers"],
        query_params=test_case["query_params"],
        raise_on_error=False,
    )

    assert response["status_code"] == test_case["expected_status"], f"{test_case['scenario']} failed on status code"
    assert response["body"] == test_case["expected_body"], f"{test_case['scenario']} failed on response body"
    assert response["headers"].get("Content-Type".lower()) == "application/fhir+json"


@pytest.mark.errorscenarios
def test_no_config_error(eligibility_client):
    expected_response = {
        "id": "<ignored>",
        "issue": [
            {
                "code": "processing",
                "details": {
                    "coding": [
                        {
                            "code": "INTERNAL_SERVER_ERROR",
                            "display": "An unexpected internal server error occurred.",
                            "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                        }
                    ]
                },
                "diagnostics": "An unexpected error occurred.",
                "severity": "error",
            }
        ],
        "meta": {"lastUpdated": "<ignored>"},
        "resourceType": "OperationOutcome",
    }

    delete_all_configs_from_s3()

    response = eligibility_client.make_request(
        nhs_number="9990032010", headers={"nhs-login-nhs-number": "9990032010"}, raise_on_error=False
    )

    assert response["status_code"] == http.HTTPStatus.INTERNAL_SERVER_ERROR
    assert response["body"] == expected_response
    assert response["headers"].get("Content-Type".lower()) == "application/fhir+json"
