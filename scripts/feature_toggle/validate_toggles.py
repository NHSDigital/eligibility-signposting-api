import json
import logging
import os
import sys

import boto3

logging.basicConfig(level=logging.INFO, format='%(message)s')


def validate_feature_toggles():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    toggles_file_path = os.path.join(script_dir, "feature_toggle.json")
    toggles_file_name = os.path.basename(toggles_file_path)

    try:
        environment = os.getenv("ENV")
        if not environment:
            raise KeyError("The 'ENV' environment variable is not set.")

        logging.info(f"Verifying toggles from '{toggles_file_name}' in environment: {environment}")

        if not os.path.exists(toggles_file_path):
            logging.error(f"FATAL: '{toggles_file_path}' not found.")
            sys.exit(1)

        with open(toggles_file_path, "r") as f:
            toggles_data = json.load(f)

        ssm_client = boto3.client("ssm")
        missing_toggles = []
        mismatched_toggles = []

        for toggle_name, toggle_details in toggles_data.items():
            parameter_name = f"/{environment}/feature_toggles/{toggle_name}"

            default_state = toggle_details.get('default_state', False)
            env_overrides = toggle_details.get('env_overrides', {})
            expected_state = env_overrides.get(environment, default_state)
            expected_state_str = str(expected_state).lower()

            logging.info(f"Checking for: {parameter_name} (expected value: {expected_state_str})")

            try:
                parameter = ssm_client.get_parameter(Name=parameter_name)
                actual_state = parameter['Parameter']['Value']

                if actual_state.lower() != expected_state_str:
                    logging.error(f"--> MISMATCH: {parameter_name} - Expected '{expected_state_str}', but found '{actual_state}'")
                    mismatched_toggles.append((parameter_name, expected_state_str, actual_state))

            except ssm_client.exceptions.ParameterNotFound:
                logging.error(f"--> MISSING: {parameter_name}")
                missing_toggles.append(parameter_name)

        has_errors = False
        if missing_toggles:
            has_errors = True
            logging.error(
                f"\nERROR: The following required feature toggles were not found in SSM:")
            for toggle in missing_toggles:
                logging.error(f"- {toggle}")

        if mismatched_toggles:
            has_errors = True
            logging.error(
                f"\nERROR: The following feature toggles have incorrect values in SSM:")
            for name, expected, actual in mismatched_toggles:
                logging.error(f"- {name}: Expected '{expected}', but found '{actual}'")

        if has_errors:
            sys.exit(1)

        logging.info(f"\nSuccess: All required feature toggles are present in SSM with the correct values.")

    except KeyError as e:
        logging.error(f"FATAL: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"FATAL: Could not decode JSON from '{toggles_file_path}'. Please check for syntax errors.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    validate_feature_toggles()
