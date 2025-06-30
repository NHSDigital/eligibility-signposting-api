import os
import json

from .dynamo_helper import insert_into_dynamo
from .placeholder_utils import resolve_placeholders
from .placeholder_context import ResolvedPlaceholderContext, PlaceholderDTO

def initialise_tests(folder):
    folder_path = os.path.abspath(folder)
    all_data, dto = load_all_test_scenarios(folder_path)

    # Insert to Dynamo (placeholder)
    for scenario in all_data.values():
        insert_into_dynamo(scenario["dynamo_items"])

    return all_data, dto

def resolve_placeholders_in_data(data, context, file_name):
    if isinstance(data, dict):
        return {k: resolve_placeholders_in_data(v, context, file_name) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_placeholders_in_data(item, context, file_name) for item in data]
    else:
        return resolve_placeholders(data, context, file_name)


def load_test_scenario(file_path):
    with open(file_path, "r") as f:
        raw_data = json.load(f)

    file_name = os.path.basename(file_path)
    context = ResolvedPlaceholderContext()
    resolved_data = resolve_placeholders_in_data(raw_data["data"], context, file_name)

    return {
        "file": file_name,
        "scenario_name": raw_data.get("scenario_name"),
        "data": resolved_data,
        "placeholders": context.all()  # Now just placeholder → value
    }


def extract_nhs_number_from_data(data):
    def find_nhs(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower().replace("_", "") == "nhsnumber":
                    return v
                elif isinstance(v, (dict, list)):
                    result = find_nhs(v)
                    if result:
                        return result
        elif isinstance(obj, list):
            for item in obj:
                result = find_nhs(item)
                if result:
                    return result
        return None

    return find_nhs(data) or "UNKNOWN"


def load_all_expected_responses(folder_path):
    all_data = {}
    dto = PlaceholderDTO()  # Shared across all files

    for filename in os.listdir(folder_path):
        if not filename.endswith(".json"):
            continue

        full_path = os.path.join(folder_path, filename)

        # Load JSON
        with open(full_path, "r") as f:
                raw_json = json.load(f)

        resolved_data = resolve_placeholders_in_data(raw_json, dto, filename)
        cleaned_data = clean_expected_response(resolved_data,)

        all_data[filename] = {
            "response_items": cleaned_data
        }

    return all_data

def load_all_test_scenarios(folder_path, config_folder_path="tests/e2e/data/configs"):
    all_data = {}
    dto = PlaceholderDTO()  # Shared across all files

    for filename in os.listdir(folder_path):
        if not filename.endswith(".json"):
            continue

        full_path = os.path.join(folder_path, filename)

        # Load scenario JSON
        with open(full_path, "r") as f:
            raw_json = json.load(f)

        raw_data = raw_json["data"]

        config_filename = raw_json.get("config_filename")  # Just the name
        scenario_name = raw_json.get("scenario_name")  # Just the name

        # Resolve placeholders with shared DTO
        resolved_data = resolve_placeholders_in_data(raw_data, dto, filename)

        # Extract NHS number
        nhs_number = extract_nhs_number_from_data(resolved_data)

        # Add resolved scenario
        all_data[filename] = {
            "dynamo_items": resolved_data,
            "nhs_number": nhs_number,
            "config_filename": config_filename,
            "scenario_name": scenario_name,
        }

    return all_data, dto

def clean_expected_response(data: dict) -> dict:
    keys_to_ignore = ["responseId", "lastUpdated"]
    return _remove_volatile_fields(data, keys_to_ignore)


def _remove_volatile_fields(data, keys_to_remove):
    if isinstance(data, dict):
        return {
            key: _remove_volatile_fields(value, keys_to_remove)
            for key, value in data.items()
            if key not in keys_to_remove
        }
    elif isinstance(data, list):
        return [_remove_volatile_fields(item, keys_to_remove) for item in data]
    return data

