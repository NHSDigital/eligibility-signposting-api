import http
import os

import pytest

from tests.e2e.tests.test_config import *
from tests.e2e.utils.data_loader import load_all_expected_responses, initialise_tests
from tests.e2e.utils.s3ConfigManager import S3ConfigManager

# Update the below with the configuration values specified in test_config.py
all_data, dto = initialise_tests(SMOKE_TEST_DATA)
all_expected_responses = load_all_expected_responses(SMOKE_TEST_RESPONSES)
config_path = SMOKE_TEST_CONFIGS

s3_manager = S3ConfigManager(S3_BUCKET, S3_PREFIX)

param_list = list(all_data.items())
id_list = [
    f"{filename} - {scenario.get('scenario_name', 'No Scenario')}"
    for filename, scenario in param_list
]


@pytest.mark.smoketest
@pytest.mark.parametrize("filename, scenario", param_list, ids=id_list)
def test_run_smoke_case(filename, scenario, eligibility_client):
    # get the nhs_number from the scenario
    nhs_number = scenario["nhs_number"]
    # get the associated campaign config file from the scenario
    config_filename = scenario.get("config_filename", "")
    # upload that config file to s3 if it is missing or has changed
    s3_manager.upload_if_missing_or_changed(os.path.abspath(os.path.join(config_path, config_filename)))

    actual_response = eligibility_client.make_request(nhs_number, strict_ssl=False)
    expected_response = all_expected_responses.get(filename).get("response_items", {})

    # Assert and show details on failure
    assert actual_response["status_code"] == 200
    assert actual_response["body"] == expected_response, (
        f"\n❌ Mismatch in test: {filename}\n"
        f"NHS Number: {nhs_number}\n"
        f"Expected: {expected_response}\n"
        f"Actual:   {actual_response}\n"
    )


@pytest.mark.smoketest
def test_check_for_missing_person(eligibility_client):
    nhs_number = "1234567890"

    request_headers = {"authenticated_nhs_number": "1234567890"},

    expected_body = {
        "issue": [{
            "code": "nhs-number-not-found",
            "diagnostics": f'NHS Number "{nhs_number}" not found.',
            "severity": "information"
        }],
        "resourceType": "OperationOutcome"
    }

    response = eligibility_client.make_request(nhs_number, headers= request_headers, raise_on_error=False)

    assert response["status_code"] == http.HTTPStatus.NOT_FOUND
    assert response["body"] == expected_body
