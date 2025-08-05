import json
import sys
from pathlib import Path

from rules_validation_api.validators.rules_validator import RulesValidation


def main() -> None:
    with Path.open(Path("campaign_config.json")) as file:
        json_data = json.load(file)  # this validates json
        RulesValidation(**json_data)
        sys.stdout.write("Valid Config\n")


if __name__ == "__main__":
    main()
