import logging
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from flask import request

from eligibility_signposting_api.common import request_validator
from eligibility_signposting_api.common.request_validator import logger
from tests.integration.conftest import UNIQUE_CONSUMER_HEADER


@pytest.fixture(autouse=True)
def setup_logging_for_tests():
    logger.handlers = []
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.NullHandler())


class TestValidateNHSNumber:
    @pytest.mark.parametrize(
        ("path_nhs", "header_nhs", "expected_result", "expected_log_msg"),
        [
            ("1234567890", None, False, "NHS number mismatch"),
            ("1234567890", "", False, "NHS number mismatch"),
            ("1234567890", "0987654321", False, "NHS number mismatch"),
            ("1234567890", "1234567890", True, None),
        ],
    )
    def test_validate_nhs_number_in_header(self, path_nhs, header_nhs, expected_result, expected_log_msg, caplog):
        with caplog.at_level(logging.ERROR):
            result = request_validator.validate_nhs_number_in_header(path_nhs, header_nhs)

        assert result == expected_result

        if expected_log_msg:
            assert any(expected_log_msg in record.message for record in caplog.records)
        else:
            assert not caplog.records


class TestValidateRequestParams:
    @pytest.mark.parametrize(
        "headers",
        [
            {},  # nhs header missing entirely - request from application restricted consumer
            {"nhs-login-nhs-number": "1234567890"},  # valid request from consumer
        ],
    )
    def test_validate_request_params_success(self, headers, app, caplog):
        mock_api = MagicMock(return_value="success")

        decorator = request_validator.validate_request_params()
        dummy_route = decorator(mock_api)

        with app.test_request_context(
            "/dummy?id=1234567890",
            headers={UNIQUE_CONSUMER_HEADER: "some-consumer"} | headers,
            method="GET",
        ):
            with caplog.at_level(logging.INFO):
                response = dummy_route(nhs_number=request.args.get("id"))

            assert response == "success"
            assert any("NHS numbers from the request" in record.message for record in caplog.records)
            assert not any(record.levelname == "ERROR" for record in caplog.records)

    @pytest.mark.parametrize(
        "headers",
        [
            {"nhs-login-nhs-number": None},  # not valid
            {"nhs-login-nhs-number": ""},  # not valid
            {"nhs-login-nhs-number": "9834567890"},  # not valid, due to mismatch
        ],
    )
    def test_validate_request_params_nhs_mismatch(self, headers, app, caplog):
        mock_api = MagicMock()

        decorator = request_validator.validate_request_params()
        dummy_route = decorator(mock_api)

        with app.test_request_context(
            "/dummy?id=1234567890",
            headers={UNIQUE_CONSUMER_HEADER: "some-id"} | headers,
            method="GET",
        ):
            with caplog.at_level(logging.INFO):
                response = dummy_route(nhs_number=request.args.get("id"))

            mock_api.assert_not_called()

            assert response is not None
            assert response.status_code == HTTPStatus.FORBIDDEN
            response_json = response.json
            issue = response_json["issue"][0]
            assert issue["code"] == "forbidden"
            assert issue["details"]["coding"][0]["code"] == "ACCESS_DENIED"
            assert issue["details"]["coding"][0]["display"] == "Access has been denied to process this request."
            assert issue["diagnostics"] == "You are not authorised to request information for the supplied NHS Number"
            assert response.headers["Content-Type"] == "application/fhir+json"

    def test_validate_request_params_consumer_id_present(self, app, caplog):
        mock_api = MagicMock(return_value="ok")

        decorator = request_validator.validate_request_params()
        dummy_route = decorator(mock_api)

        with (
            app.test_request_context(
                "/dummy?id=1234567890",
                headers={
                    UNIQUE_CONSUMER_HEADER: "some-consumer",
                    "nhs-login-nhs-number": "1234567890",
                },
                method="GET",
            ),
            caplog.at_level(logging.INFO),
        ):
            response = dummy_route(nhs_number=request.args.get("id"))

        mock_api.assert_called_once()
        assert response == "ok"
        assert not any(record.levelname == "ERROR" for record in caplog.records)

    def test_validate_request_params_missing_consumer_id(self, app, caplog):
        mock_api = MagicMock()

        decorator = request_validator.validate_request_params()
        dummy_route = decorator(mock_api)

        with (
            app.test_request_context(
                "/dummy?id=1234567890",
                headers={"nhs-login-nhs-number": "1234567890"},  # no consumer ID
                method="GET",
            ),
            caplog.at_level(logging.ERROR),
        ):
            response = dummy_route(nhs_number=request.args.get("id"))

        mock_api.assert_not_called()

        assert response is not None
        assert response.status_code == HTTPStatus.FORBIDDEN
        response_json = response.json

        issue = response_json["issue"][0]
        assert issue["code"] == "forbidden"
        assert issue["details"]["coding"][0]["code"] == "ACCESS_DENIED"
        assert issue["details"]["coding"][0]["display"] == "Access has been denied to process this request."
        assert issue["diagnostics"] == "You are not authorised to request"
        assert response.headers["Content-Type"] == "application/fhir+json"


class TestValidateQueryParameters:
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
    def test_validate_query_params_conditions(self, conditions_input, is_valid_expected, expected_log_msg, caplog):
        params = {"conditions": conditions_input}

        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)

        assert is_valid == is_valid_expected
        if is_valid_expected:
            assert problem is None
            assert not caplog.records
        else:
            assert problem is not None
            assert any(
                (record.levelname == "ERROR" and expected_log_msg in record.message) for record in caplog.records
            )

    def test_validate_query_params_conditions_default(self, caplog):
        params = {"category": "ALL", "includeActions": "Y"}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
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
    def test_validate_query_params_category(self, category_input, is_valid_expected, expected_log_msg, caplog):
        params = {"category": category_input}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
        assert is_valid == is_valid_expected

        if is_valid_expected:
            assert problem is None
            assert not caplog.records
        else:
            assert problem is not None
            assert any(
                (record.levelname == "ERROR" and expected_log_msg in record.message) for record in caplog.records
            )

    def test_validate_query_params_category_default(self, caplog):
        params = {"conditions": "ALL", "includeActions": "Y"}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
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
    def test_validate_query_params_include_actions(
        self, include_actions_input, is_valid_expected, expected_log_msg, caplog
    ):
        params = {"includeActions": include_actions_input}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
        assert is_valid == is_valid_expected

        if is_valid_expected:
            assert problem is None
            assert not caplog.records
        else:
            assert problem is not None
            assert any(
                (record.levelname == "ERROR" and expected_log_msg in record.message) for record in caplog.records
            )

    def test_validate_query_params_include_actions_default(self, caplog):
        params = {"conditions": "ALL", "category": "ALL"}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
        assert is_valid is True
        assert problem is None
        assert not caplog.records

    def test_validate_query_params_all_valid_params(self, caplog):
        params = {"conditions": "COND1,COND2", "category": "SCREENING", "includeActions": "N"}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
        assert is_valid is True
        assert problem is None
        assert not caplog.records

    def test_validate_query_params_mixed_valid_invalid_conditions_fail_first(self, caplog):
        params = {"conditions": "VALID_COND,INVALID!,ANOTHER_VALID", "category": "SCREENING", "includeActions": "N"}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
        assert is_valid is False
        assert problem is not None
        assert any(
            (record.levelname == "ERROR" and "Invalid condition query param: " in record.message)
            for record in caplog.records
        )

    def test_validate_query_params_valid_conditions_invalid_category_fail_second(self, caplog):
        params = {"conditions": "CONDITION", "category": "BAD_CAT", "includeActions": "N"}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
        assert is_valid is False
        assert problem is not None
        assert any(
            (record.levelname == "ERROR" and "Invalid category query param: " in record.message)
            for record in caplog.records
        )
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) == 1

    def test_validate_query_params_valid_conditions_category_invalid_actions_fail_third(self, caplog):
        params = {"conditions": "CONDITION", "category": "VACCINATIONS", "includeActions": "Nope"}
        with caplog.at_level(logging.ERROR):
            is_valid, problem = request_validator.validate_query_params(params)
        assert is_valid is False
        assert problem is not None
        assert any(
            (record.levelname == "ERROR" and "Invalid include actions query param: " in record.message)
            for record in caplog.records
        )
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) == 1

    def test_validate_query_params_returns_correct_problem_details_for_conditions_error(self):
        invalid_condition = "FLU&COVID"
        params = {"conditions": invalid_condition}

        is_valid, problem = request_validator.validate_query_params(params)

        assert is_valid is False
        assert problem is not None
        assert problem.status_code == HTTPStatus.BAD_REQUEST
        assert problem.headers["Content-Type"] == "application/fhir+json"

        response_json = problem.json

        assert response_json["resourceType"] == "OperationOutcome"
        assert "id" in response_json
        assert "meta" in response_json
        assert "lastUpdated" in response_json["meta"]

        assert len(response_json["issue"]) == 1
        issue = response_json["issue"][0]

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

        assert coding["system"] == "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1"
        assert coding["code"] == "INVALID_PARAMETER"
        assert coding["display"] == "The given conditions were not in the expected format."

    def test_validate_query_params_returns_correct_problem_details_for_category_error(self):
        invalid_category = "HEALTHCHECKS"
        params = {"category": invalid_category}

        is_valid, problem = request_validator.validate_query_params(params)

        assert is_valid is False
        assert problem is not None
        assert problem.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert problem.headers["Content-Type"] == "application/fhir+json"

        response_json = problem.json

        assert response_json["resourceType"] == "OperationOutcome"
        assert "id" in response_json
        assert "meta" in response_json
        assert "lastUpdated" in response_json["meta"]

        assert len(response_json["issue"]) == 1
        issue = response_json["issue"][0]

        assert issue["severity"] == "error"
        assert issue["code"] == "value"
        assert issue["diagnostics"] == f"{invalid_category} is not a category that is supported by the API"
        assert issue["location"] == ["parameters/category"]
        assert "details" in issue
        assert "coding" in issue["details"]
        assert len(issue["details"]["coding"]) == 1
        coding = issue["details"]["coding"][0]

        assert coding["system"] == "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1"
        assert coding["code"] == "INVALID_PARAMETER"
        assert coding["display"] == "The supplied category was not recognised by the API."

    def test_validate_query_params_returns_correct_problem_details_for_include_actions_error(self):
        invalid_include_actions = "NAH"
        params = {"includeActions": invalid_include_actions}

        is_valid, problem = request_validator.validate_query_params(params)

        assert is_valid is False
        assert problem is not None
        assert problem.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert problem.headers["Content-Type"] == "application/fhir+json"

        response_json = problem.json

        assert response_json["resourceType"] == "OperationOutcome"
        assert "id" in response_json
        assert "meta" in response_json
        assert "lastUpdated" in response_json["meta"]

        assert len(response_json["issue"]) == 1
        issue = response_json["issue"][0]

        assert issue["severity"] == "error"
        assert issue["code"] == "value"
        assert issue["diagnostics"] == f"{invalid_include_actions} is not a value that is supported by the API"
        assert issue["location"] == ["parameters/includeActions"]
        assert "details" in issue
        assert "coding" in issue["details"]
        assert len(issue["details"]["coding"]) == 1
        coding = issue["details"]["coding"][0]

        assert coding["system"] == "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1"
        assert coding["code"] == "INVALID_PARAMETER"
        assert coding["display"] == "The supplied value was not recognised by the API."
