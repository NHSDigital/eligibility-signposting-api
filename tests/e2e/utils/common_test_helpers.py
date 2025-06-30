def clean_response(data: dict) -> dict:
    keys_to_ignore = ["responseId", "lastUpdated"]
    return remove_volatile_fields(data, keys_to_ignore)


def remove_volatile_fields(data, keys_to_remove):
    if isinstance(data, dict):
        return {
            key: remove_volatile_fields(value, keys_to_remove)
            for key, value in data.items()
            if key not in keys_to_remove
        }
    elif isinstance(data, list):
        return [remove_volatile_fields(item, keys_to_remove) for item in data]
    return data
