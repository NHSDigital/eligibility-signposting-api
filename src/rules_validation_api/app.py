import argparse
import json
import sys
from pathlib import Path

from rules_validation_api.validators.rules_validator import RulesValidation

GREEN = "\033[92m"
RESET = "\033[0m"
YELLOW = "\033[93m"
RED = "\033[91m"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate campaign configuration.")
    parser.add_argument("--config_path", required=True, help="Path to the campaign config JSON file")
    args = parser.parse_args()

    try:
        with Path(args.config_path).open() as file:
            json_data = json.load(file)
            RulesValidation(**json_data)
            sys.stdout.write(f"{GREEN}Valid Config{RESET}\n")
    except ValueError as e:
        sys.stderr.write(f"{YELLOW}Validation Error:{RESET} {RED}{e}{RESET}\n")


if __name__ == "__main__":
    main()
