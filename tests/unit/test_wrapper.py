import json
import logging
from http import HTTPStatus

import pytest

from eligibility_signposting_api import wrapper
from eligibility_signposting_api.wrapper import logger


@pytest.fixture(autouse=True)
def setup_logging_for_tests():
    logger.handlers = []
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.NullHandler())


@pytest.mark.parametrize(
    ("path_nhs", "header_nhs", "expected_result", "expected_log_msg"),
    [
        (None, None, False, "NHS number is not present"),
        ("1234567890", None, False, "NHS number is not present"),
        (None, "1234567890", False, "NHS number is not present"),
        ("1234567890", "0987654321", False, "NHS number mismatch"),
        ("1234567890", "1234567890", True, None),
    ],
)
def test_validate_nhs_number(path_nhs, header_nhs, expected_result, expected_log_msg, caplog):
    with caplog.at_level(logging.ERROR):
        result = wrapper.validate_nhs_number(path_nhs, header_nhs)

    assert result == expected_result

    if expected_log_msg:
        assert any(expected_log_msg in record.message for record in caplog.records)
    else:
        assert not caplog.records


@pytest.mark.parametrize(
    ("conditions_input", "is_valid_expected", "expected_log_msg"),
    [
        ("ALL", True, None),
        ("COVID", True, None),
        ("covid19", True, None),
        ("FLU,MMR", True, None),
        ("  RSV , COVID19", True, None),
        ("  condition_with_spaces  ", False, "Invalid condition query param: '  condition_with_spaces  '"),
        ("CONDITION_A,ANOTHER_ONE,123ABC", False, "Invalid condition query param: 'CONDITION_A'"),
        ("condition1,", False, "Invalid condition query param: ''"),
        (",condition2", False, "Invalid condition query param: ''"),
        ("condition-invalid", False, "Invalid condition query param: 'condition-invalid'"),
        ("condition with spaces", False, "Invalid condition query param: 'condition with spaces'"),
        ("condition!", False, "Invalid condition query param: 'condition!'"),
        ("condition@#$", False, "Invalid condition query param: 'condition@#$'"),
    ],
)
def test_validate_query_params_conditions(conditions_input, is_valid_expected, expected_log_msg, caplog):
    params = {"conditions": conditions_input}

    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)

    assert is_valid == is_valid_expected
    if is_valid_expected:
        assert problem is None
        assert not caplog.records
    else:
        assert problem is not None
        assert any((record.levelname == "ERROR" and expected_log_msg in record.message) for record in caplog.records)


def test_validate_query_params_conditions_default(caplog):
    params = {"category": "ALL", "includeActions": "Y"}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid is True
    assert problem is None
    assert not caplog.records


@pytest.mark.parametrize(
    ("category_input", "is_valid_expected", "expected_log_msg"),
    [
        ("VACCINATIONS", True, None),
        ("SCREENING", True, None),
        ("ALL", True, None),
        ("vaccinations", True, None),
        ("screening", True, None),
        ("all", True, None),
        (" VACCINATIONS ", True, None),
        ("OTHER_CATEGORY    ", False, "Invalid category query param: 'OTHER_CATEGORY    '"),
        ("invalid!", False, "Invalid category query param: 'invalid!'"),
        ("VACCINATION", False, "Invalid category query param: 'VACCINATION'"),
    ],
)
def test_validate_query_params_category(category_input, is_valid_expected, expected_log_msg, caplog):
    params = {"category": category_input}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid == is_valid_expected

    if is_valid_expected:
        assert problem is None
        assert not caplog.records
    else:
        assert problem is not None
        assert any((record.levelname == "ERROR" and expected_log_msg in record.message) for record in caplog.records)


def test_validate_query_params_category_default(caplog):
    params = {"conditions": "ALL", "includeActions": "Y"}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid is True
    assert problem is None
    assert not caplog.records


@pytest.mark.parametrize(
    ("include_actions_input", "is_valid_expected", "expected_log_msg"),
    [
        ("Y", True, None),
        ("N", True, None),
        ("y", True, None),
        ("n", True, None),
        ("n  ", True, None),
        ("TRUE", False, "Invalid include actions query param: 'TRUE'"),
        ("YES", False, "Invalid include actions query param: 'YES'"),
        ("0", False, "Invalid include actions query param: '0'"),
        ("1", False, "Invalid include actions query param: '1'"),
        ("", False, "Invalid include actions query param: ''"),
        (" ", False, "Invalid include actions query param: ' '"),
    ],
)
def test_validate_query_params_include_actions(include_actions_input, is_valid_expected, expected_log_msg, caplog):
    params = {"includeActions": include_actions_input}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid == is_valid_expected

    if is_valid_expected:
        assert problem is None
        assert not caplog.records
    else:
        assert problem is not None
        assert any((record.levelname == "ERROR" and expected_log_msg in record.message) for record in caplog.records)


def test_validate_query_params_include_actions_default(caplog):
    params = {"conditions": "ALL", "category": "ALL"}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid is True
    assert problem is None
    assert not caplog.records


def test_validate_query_params_all_valid_params(caplog):
    params = {"conditions": "COND1,COND2", "category": "SCREENING", "includeActions": "N"}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid is True
    assert problem is None
    assert not caplog.records


def test_validate_query_params_mixed_valid_invalid_conditions_fail_first(caplog):
    params = {"conditions": "VALID_COND,INVALID!,ANOTHER_VALID", "category": "SCREENING", "includeActions": "N"}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid is False
    assert problem is not None
    assert any(
        (record.levelname == "ERROR" and "Invalid condition query param: " in record.message)
        for record in caplog.records
    )


def test_validate_query_params_valid_conditions_invalid_category_fail_second(caplog):
    params = {"conditions": "CONDITION", "category": "BAD_CAT", "includeActions": "N"}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid is False
    assert problem is not None
    assert any(
        (record.levelname == "ERROR" and "Invalid category query param: " in record.message)
        for record in caplog.records
    )
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) == 1


def test_validate_query_params_valid_conditions_category_invalid_actions_fail_third(caplog):
    params = {"conditions": "CONDITION", "category": "VACCINATIONS", "includeActions": "Nope"}
    with caplog.at_level(logging.ERROR):
        is_valid, problem = wrapper.validate_query_params(params)
    assert is_valid is False
    assert problem is not None
    assert any(
        (record.levelname == "ERROR" and "Invalid include actions query param: " in record.message)
        for record in caplog.records
    )
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) == 1


def test_validate_query_params_returns_correct_problem_details_for_conditions_error():
    invalid_condition = "FLU&COVID"
    params = {"conditions": invalid_condition}

    is_valid, problem = wrapper.validate_query_params(params)

    assert is_valid is False
    assert problem is not None
    assert problem["statusCode"] == HTTPStatus.BAD_REQUEST
    assert problem["headers"]["Content-Type"] == "application/fhir+json"

    response_body = json.loads(problem["body"])

    assert response_body["resourceType"] == "OperationOutcome"
    assert "id" in response_body
    assert "meta" in response_body
    assert "lastUpdated" in response_body["meta"]

    assert len(response_body["issue"]) == 1
    issue = response_body["issue"][0]

    assert issue["severity"] == "error"
    assert issue["code"] == "value"
    assert issue["diagnostics"] == (
        f"{invalid_condition} should be a single or comma separated list of condition "
        f"strings with no other punctuation or special characters"
    )
    assert issue["location"] == ["parameters/conditions"]
    assert "details" in issue
    assert "coding" in issue["details"]
    assert len(issue["details"]["coding"]) == 1
    coding = issue["details"]["coding"][0]

    assert coding["system"] == "https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode"
    assert coding["code"] == "VALIDATION_ERROR"
    assert coding["display"] == "The given conditions were not in the expected format."


def test_validate_query_params_returns_correct_problem_details_for_category_error():
    invalid_category = "HEALTHCHECKS"
    params = {"category": invalid_category}

    is_valid, problem = wrapper.validate_query_params(params)

    assert is_valid is False
    assert problem is not None
    assert problem["statusCode"] == HTTPStatus.UNPROCESSABLE_ENTITY
    assert problem["headers"]["Content-Type"] == "application/fhir+json"

    response_body = json.loads(problem["body"])

    assert response_body["resourceType"] == "OperationOutcome"
    assert "id" in response_body
    assert "meta" in response_body
    assert "lastUpdated" in response_body["meta"]

    assert len(response_body["issue"]) == 1
    issue = response_body["issue"][0]

    assert issue["severity"] == "error"
    assert issue["code"] == "value"
    assert issue["diagnostics"] == f"{invalid_category} is not a category that is supported by the API"
    assert issue["location"] == ["parameters/category"]
    assert "details" in issue
    assert "coding" in issue["details"]
    assert len(issue["details"]["coding"]) == 1
    coding = issue["details"]["coding"][0]

    assert coding["system"] == "https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode"
    assert coding["code"] == "VALIDATION_ERROR"
    assert coding["display"] == "The supplied category was not recognised by the API."


def test_validate_query_params_returns_correct_problem_details_for_include_actions_error():
    invalid_include_actions = "NAH"
    params = {"includeActions": invalid_include_actions}

    is_valid, problem = wrapper.validate_query_params(params)

    assert is_valid is False
    assert problem is not None
    assert problem["statusCode"] == HTTPStatus.UNPROCESSABLE_ENTITY
    assert problem["headers"]["Content-Type"] == "application/fhir+json"

    response_body = json.loads(problem["body"])

    assert response_body["resourceType"] == "OperationOutcome"
    assert "id" in response_body
    assert "meta" in response_body
    assert "lastUpdated" in response_body["meta"]

    assert len(response_body["issue"]) == 1
    issue = response_body["issue"][0]

    assert issue["severity"] == "error"
    assert issue["code"] == "value"
    assert issue["diagnostics"] == f"{invalid_include_actions} is not a value that is supported by the API"
    assert issue["location"] == ["parameters/includeActions"]
    assert "details" in issue
    assert "coding" in issue["details"]
    assert len(issue["details"]["coding"]) == 1
    coding = issue["details"]["coding"][0]

    assert coding["system"] == "https://fhir.nhs.uk/CodeSystem/Spine-ErrorOrWarningCode"
    assert coding["code"] == "VALIDATION_ERROR"
    assert coding["display"] == "The supplied value was not recognised by the API."
