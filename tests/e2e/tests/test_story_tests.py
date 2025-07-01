import http
import os

import pytest

from tests.e2e.tests.test_config import *
from tests.e2e.utils.data_loader import load_all_expected_responses, initialise_tests
from tests.e2e.utils.s3ConfigManager import S3ConfigManager

# Update the below with the configuration values specified in test_config.py
all_data, dto = initialise_tests(STORY_TEST_DATA)
all_expected_responses = load_all_expected_responses(STORY_TEST_RESPONSES)
config_path = STORY_TEST_CONFIGS

s3_manager = S3ConfigManager(S3_BUCKET, S3_PREFIX)

param_list = list(all_data.items())
id_list = [
    f"{filename} - {scenario.get('scenario_name', 'No Scenario')}"
    for filename, scenario in param_list
]


@pytest.mark.storytest_all
@pytest.mark.parametrize("filename, scenario", param_list, ids=id_list)
def test_run_story_test_cases(filename, scenario, eligibility_client):
    nhs_number = scenario["nhs_number"]
    config_filename = scenario.get("config_filename", "")
    request_headers = scenario.get("request_headers", {})
    s3_manager.upload_if_missing_or_changed(os.path.abspath(os.path.join(config_path, config_filename)))

    actual_response = eligibility_client.make_request(nhs_number, strict_ssl=False)
    expected_response = all_expected_responses.get(filename).get("response_items", {})

    # Assert and show details on failure
    assert actual_response["status_code"] == http.HTTPStatus.OK
    assert actual_response["body"] == expected_response, (
        f"\n❌ Mismatch in test: {filename}\n"
        f"NHS Number: {nhs_number}\n"
        f"Expected: {expected_response}\n"
        f"Actual:   {actual_response}\n"
    )
