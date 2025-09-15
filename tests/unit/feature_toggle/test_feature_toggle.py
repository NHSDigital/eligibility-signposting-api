import os
from unittest.mock import patch, Mock
from botocore.exceptions import ClientError

os.environ["AWS_DEFAULT_REGION"] = "eu-west-2"
os.environ["ENV"] = "local"

import pytest

from eligibility_signposting_api.feature_toggle.feature_toggle import (
    get_ssm_parameter,
    is_feature_enabled,
    ssm_cache_in_seconds,
)


@pytest.fixture(autouse=True)
def clear_cache():
    ssm_cache_in_seconds.clear()
    yield


@patch("eligibility_signposting_api.feature_toggle.feature_toggle.ssm_client")
class TestGetSsmParameter:
    def test_get_ssm_parameter_success(self, mock_ssm_client: Mock):
        param_name = "/local/feature_toggles/feature_test"
        expected_value = "true"
        mock_ssm_client.get_parameter.return_value = {
            "Parameter": {"Value": expected_value}
        }

        result = get_ssm_parameter(param_name)

        assert result == expected_value
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name=param_name, WithDecryption=True
        )

    def test_get_ssm_parameter_is_cached(self, mock_ssm_client: Mock):
        param_name = "/local/feature_toggles/cached_feature"
        expected_value = "true"
        mock_ssm_client.get_parameter.return_value = {
            "Parameter": {"Value": expected_value}
        }

        result1 = get_ssm_parameter(param_name)
        result2 = get_ssm_parameter(param_name)

        assert result1 == expected_value
        assert result2 == expected_value
        mock_ssm_client.get_parameter.assert_called_once()

    def test_get_ssm_parameter_not_found(self, mock_ssm_client: Mock):
        param_name = "/local/feature_toggles/non_existent_feature"

        not_found_error = ClientError(
            error_response={"Error": {"Code": "ParameterNotFound", "Message": "Not Found"}},
            operation_name="GetParameter",
        )

        mock_ssm_client.exceptions.ParameterNotFound = ClientError

        mock_ssm_client.get_parameter.side_effect = not_found_error

        result = get_ssm_parameter(param_name)

        assert result == "false"
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name=param_name, WithDecryption=True
        )

    def test_get_ssm_parameter_client_error(self, mock_ssm_client: Mock):
        param_name = "/local/feature_toggles/error_feature"

        mock_ssm_client.exceptions.ParameterNotFound = ClientError
        mock_ssm_client.get_parameter.side_effect = ClientError(
            error_response={"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            operation_name="GetParameter",
        )

        result = get_ssm_parameter(param_name)

        assert result == "false"


@patch("eligibility_signposting_api.feature_toggle.feature_toggle.get_ssm_parameter")
class TestIsFeatureEnabled:
    @pytest.mark.parametrize(
        "return_value, expected_result",
        [
            ("true", True),
            ("True", True),
            (" TRUE ", True),
            ("false", False),
            ("False", False),
            ("anything_else", False),
            ("", False),
        ],
    )
    def test_is_feature_enabled_various_inputs(
        self, mock_get_ssm_parameter: Mock, return_value: str, expected_result: bool
    ):
        feature_name = "is_feature_enabled_test"
        expected_param_name = f"/local/feature_toggles/{feature_name}"
        mock_get_ssm_parameter.return_value = return_value

        result = is_feature_enabled(feature_name)

        assert result is expected_result
        mock_get_ssm_parameter.assert_called_once_with(expected_param_name)
