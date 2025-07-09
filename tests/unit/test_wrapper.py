import logging

import pytest

from eligibility_signposting_api import wrapper
from eligibility_signposting_api.wrapper import logger


@pytest.fixture(autouse=True)
def setup_logging_for_tests():
    logger.handlers = []
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.NullHandler())

@pytest.mark.parametrize(
    "path_nhs, header_nhs, expected_result, expected_log_msg",
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
        # No error logs expected if validation passes
        assert not caplog.records


@pytest.mark.parametrize(
    ("conditions_input", "expected_result", "expected_log_msg"),
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
def test_validate_query_params_conditions(conditions_input, expected_result, expected_log_msg, captured_log):
    params = {"conditions": conditions_input}

    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)

    assert result == expected_result

    if not expected_result:
        assert any(
            (record.levelname == "ERROR" and expected_log_msg in record.message) for record in captured_log.records
        )
    else:
        assert not captured_log.records


def test_validate_query_params_conditions_default(captured_log):
    params = {"category": "ALL", "includeActions": "Y"}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result is True
    assert not captured_log.records


@pytest.mark.parametrize(
    ("category_input", "expected_result", "expected_log_msg"),
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
def test_validate_query_params_category(category_input, expected_result, expected_log_msg, captured_log):
    params = {"category": category_input}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result == expected_result

    if not expected_result:
        assert any(
            (record.levelname == "ERROR" and expected_log_msg in record.message) for record in captured_log.records
        )
    else:
        assert not captured_log.records


def test_validate_query_params_category_default(captured_log):
    params = {"conditions": "ALL", "includeActions": "Y"}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result is True
    assert not captured_log.records


@pytest.mark.parametrize(
    ("include_actions_input", "expected_result", "expected_log_msg"),
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
def test_validate_query_params_include_actions(include_actions_input, expected_result, expected_log_msg, captured_log):
    params = {"includeActions": include_actions_input}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result == expected_result

    if not expected_result:
        assert any(
            (record.levelname == "ERROR" and expected_log_msg in record.message) for record in captured_log.records
        )
    else:
        assert not captured_log.records


def test_validate_query_params_include_actions_default(captured_log):
    params = {"conditions": "ALL", "category": "ALL"}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result is True
    assert not captured_log.records


def test_validate_query_params_all_valid_params(captured_log):
    params = {"conditions": "COND1,COND2", "category": "SCREENING", "includeActions": "N"}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result is True
    assert not captured_log.records


def test_validate_query_params_mixed_valid_invalid_conditions_fail_first(captured_log):
    params = {"conditions": "VALID_COND,INVALID!,ANOTHER_VALID", "category": "SCREENING", "includeActions": "N"}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result is False
    assert any(
        (record.levelname == "ERROR" and "Invalid condition query param: " in record.message)
        for record in captured_log.records
    )

    error_logs = [r for r in captured_log.records if r.levelname == "ERROR"]
    assert len(error_logs) == 1


def test_validate_query_params_valid_conditions_invalid_category_fail_second(captured_log):
    params = {"conditions": "CONDITION", "category": "BAD_CAT", "includeActions": "N"}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result is False
    assert any(
        (record.levelname == "ERROR" and "Invalid category query param: " in record.message)
        for record in captured_log.records
    )
    error_logs = [r for r in captured_log.records if r.levelname == "ERROR"]
    assert len(error_logs) == 1


def test_validate_query_params_valid_conditions_category_invalid_actions_fail_third(captured_log):
    params = {"conditions": "CONDITION", "category": "VACCINATIONS", "includeActions": "Nope"}
    with captured_log.at_level(logging.ERROR):
        result = wrapper.validate_query_params(params)
    assert result is False
    assert any(
        (record.levelname == "ERROR" and "Invalid include actions query param: " in record.message)
        for record in captured_log.records
    )
    error_logs = [r for r in captured_log.records if r.levelname == "ERROR"]
    assert len(error_logs) == 1
