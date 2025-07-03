import http
from pathlib import Path

import pytest

from tests.e2e.tests import test_config
from tests.e2e.utils.data_loader import initialise_tests, load_all_expected_responses
from tests.e2e.utils.s3_config_manager import S3ConfigManager

# Update the below with the configuration values specified in test_config.py
all_data, dto = initialise_tests(test_config.REGRESSION_TEST_DATA)
all_expected_responses = load_all_expected_responses(test_config.REGRESSION_RESPONSES)
config_path = test_config.REGRESSION_CONFIGS

s3_manager = S3ConfigManager(test_config.S3_BUCKET, test_config.S3_PREFIX)

param_list = list(all_data.items())
id_list = [f"{filename} - {scenario.get('scenario_name', 'No Scenario')}" for filename, scenario in param_list]


@pytest.mark.regressiontest
@pytest.mark.parametrize(("filename", "scenario"), param_list, ids=id_list)
def test_run_regression_tests(filename, scenario, eligibility_client):
    nhs_number = scenario["nhs_number"]
    config_filename = scenario.get("config_filename", "")
    request_headers = scenario.get("request_headers", {})
    s3_manager.upload_if_missing_or_changed((Path(config_path) / config_filename).resolve())

    actual_response = eligibility_client.make_request(nhs_number, headers=request_headers, strict_ssl=False)
    expected_response = all_expected_responses.get(filename).get("response_items", {})

    # Assert and show details on failure
    assert actual_response["status_code"] == http.HTTPStatus.OK
    assert actual_response["body"] == expected_response, (
        f"\n❌ Mismatch in test: {filename}\n"
        f"NHS Number: {nhs_number}\n"
        f"Expected: {expected_response}\n"
        f"Actual:   {actual_response}\n"
    )
