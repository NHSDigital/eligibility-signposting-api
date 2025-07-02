import json
from pathlib import Path

from .dynamo_helper import insert_into_dynamo
from .placeholder_context import PlaceholderDTO, ResolvedPlaceholderContext
from .placeholder_utils import resolve_placeholders


def initialise_tests(folder):
    folder_path = Path(folder).resolve()
    all_data, dto = load_all_test_scenarios(folder_path)

    # Insert to Dynamo (placeholder)
    for scenario in all_data.values():
        insert_into_dynamo(scenario["dynamo_items"])

    return all_data, dto


def resolve_placeholders_in_data(data, context, file_name):
    if isinstance(data, dict):
        return {k: resolve_placeholders_in_data(v, context, file_name) for k, v in data.items()}
    if isinstance(data, list):
        return [resolve_placeholders_in_data(item, context, file_name) for item in data]
    return resolve_placeholders(data, context, file_name)


def load_test_scenario(file_path):
    with Path.open(file_path) as f:
        raw_data = json.load(f)

    file_name = Path(file_path).name
    context = ResolvedPlaceholderContext()
    resolved_data = resolve_placeholders_in_data(raw_data["data"], context, file_name)

    return {
        "file": file_name,
        "scenario_name": raw_data.get("scenario_name"),
        "data": resolved_data,
        "placeholders": context.all(),  # Now just placeholder → value
    }


def extract_nhs_number_from_data(data):
    def find_nhs(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower().replace("_", "") == "nhsnumber":
                    return v
                if isinstance(v, (dict, list)):
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

    for path in Path(folder_path).iterdir():
        if path.suffix != ".json":
            continue

        with path.open() as f:
            raw_json = json.load(f)

        resolved_data = resolve_placeholders_in_data(raw_json, dto, path.name)
        cleaned_data = clean_expected_response(resolved_data)

        all_data[path.name] = {"response_items": cleaned_data}

    return all_data


def load_all_test_scenarios(folder_path):
    all_data = {}
    dto = PlaceholderDTO()  # Shared across all files

    for path in Path(folder_path).iterdir():
        if path.suffix != ".json":
            continue

        with path.open() as f:
            raw_json = json.load(f)

        raw_data = raw_json["data"]

        config_filename = raw_json.get("config_filename")
        scenario_name = raw_json.get("scenario_name")
        request_headers = raw_json.get("request_headers")
        expected_response_code = raw_json.get("expected_response_code")

        # Resolve placeholders with shared DTO
        resolved_data = resolve_placeholders_in_data(raw_data, dto, path.name)

        # Extract NHS number
        nhs_number = extract_nhs_number_from_data(resolved_data)

        # Add resolved scenario
        all_data[path.name] = {
            "dynamo_items": resolved_data,
            "nhs_number": nhs_number,
            "config_filename": config_filename,
            "expected_response_code": expected_response_code,
            "request_headers": request_headers,
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
    if isinstance(data, list):
        return [_remove_volatile_fields(item, keys_to_remove) for item in data]
    return data
