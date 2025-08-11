import http

import pytest

from tests.e2e.tests import test_config
from tests.e2e.utils.data_helper import initialise_tests, load_all_expected_responses

# Update the below with the configuration values specified in test_config.py
all_data, dto = initialise_tests(test_config.VITA_INTEGRATION_TEST_DATA)
all_expected_responses = load_all_expected_responses(test_config.VITA_INTEGRATION_RESPONSES)
config_path = test_config.VITA_INTEGRATION_CONFIGS

param_list = list(all_data.items())
id_list = [f"{filename} - {scenario.get('scenario_name', 'No Scenario')}" for filename, scenario in param_list]


@pytest.mark.vitaintegration
@pytest.mark.parametrize(("filename", "scenario"), param_list, ids=id_list)
def test_run_story_test_cases(filename, scenario, eligibility_client, get_scenario_params):
    nhs_number, config_filenames, request_headers, query_params, expected_response_code = get_scenario_params(scenario, config_path)

    actual_response = eligibility_client.make_request(
        nhs_number=nhs_number, headers=request_headers, query_params=query_params, strict_ssl=False
    )
    expected_response = all_expected_responses.get(filename).get("response_items", {})

    expected_response_code = expected_response_code or http.HTTPStatus.OK

    assert actual_response["status_code"] == expected_response_code
    assert actual_response["body"] == expected_response, (
        f"\n❌ Mismatch in test: {filename}\n"
        f"NHS Number: {nhs_number}\n"
        f"Expected: {expected_response}\n"
        f"Actual:   {actual_response}\n"
    )
