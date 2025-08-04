import json
from pathlib import Path

from pydantic import ValidationError

from rules_validation_api.validators.rules_validator import RulesValidation


def main() -> None:
    with Path.open(Path("campaign_config.json")) as file:
        json_data = json.load(file)  # this validates json

    try:
        RulesValidation(**json_data)
        print("No validation errors")  # noqa: T201
    except ValidationError as e:
        print(e)  # noqa: T201


if __name__ == "__main__":
    main()
