import argparse
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from rules_validation_api.validators.rules_validator import RulesValidation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)

GREEN = "\033[92m"
RESET = "\033[0m"
YELLOW = "\033[93m"
RED = "\033[91m"


def refine_error(e: ValidationError) -> str:
    """Return a very short, single-line error message."""
    lines = [f"Validation Error: {len(e.errors())} validation error(s)"]

    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        type_ = err["type"]

        lines.append(f"{loc} : {msg} [type={type_}]")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate campaign configuration.")
    parser.add_argument("--config_path", required=True, help="Path to the campaign config JSON file")
    args = parser.parse_args()

    try:
        with Path(args.config_path).open() as file:
            json_data = json.load(file)
            RulesValidation(**json_data)
            sys.stdout.write(f"{GREEN}Valid Config{RESET}\n")

    except ValidationError as e:
        clean = refine_error(e)
        sys.stderr.write(f"{YELLOW}{clean}{RESET}\n")


if __name__ == "__main__":
    main()
