import os
from tests.e2e.utils.dynamo_helper import insert_into_dynamo
from tests.e2e.utils.data_loader import load_all_test_scenarios


def initialise_tests(folder):
    folder_path = os.path.abspath(folder)
    all_data, dto = load_all_test_scenarios(folder_path)

    # Insert to Dynamo (placeholder)
    for scenario in all_data.values():
        insert_into_dynamo(scenario["dynamo_items"])

    return all_data, dto
