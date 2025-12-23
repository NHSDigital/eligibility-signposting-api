import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

from rules_validation_api.decorators.tracker import VALIDATORS_CALLED
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

# ANSI color codes
LEFT_COLOR = "\033[34m"  # Blue for class name
COLON_COLOR = "\033[33m"  # Yellow for colon
RIGHT_COLOR = "\033[92m"  # Milk green for validator
CLASS_COLORS = [
    "\033[34m",  # blue
    "\033[35m",  # magenta
    "\033[36m",  # cyan
    "\033[94m",  # light blue
    "\033[95m",  # light magenta
    "\033[96m",  # light cyan
    "\033[37m",  # white/light grey
]

def main() -> None:
    parser = argparse.ArgumentParser(description="Validate campaign configuration.")
    parser.add_argument("--config_path", required=True, help="Path to the campaign config JSON file")
    args = parser.parse_args()

    try:
        with Path(args.config_path).open() as file:
            json_data = json.load(file)
            RulesValidation(**json_data)
            sys.stdout.write(f"{GREEN}Valid Config{RESET}\n")

            # Group by class
            grouped = defaultdict(list)
            for v in VALIDATORS_CALLED:
                cls, method = v.split(":", 1)
                grouped[cls].append(method.strip())

            # Assign colors to classes
            cls_color_map = {}
            for i, cls_name in enumerate(sorted(grouped.keys(), reverse=True)):
                cls_color_map[cls_name] = CLASS_COLORS[i % len(CLASS_COLORS)]

            # Print grouped
            for cls_name in sorted(grouped.keys(), reverse=True):
                methods = sorted(grouped[cls_name])
                # First method prints class name
                first = methods[0]
                colored = f"{cls_color_map[cls_name]}{cls_name}{RESET}{COLON_COLOR}:{RESET}{RIGHT_COLOR}{first}{RESET}"
                print(colored)
                # Rest methods indented
                for method_name in methods[1:]:
                    colored = f"{' ' * len(cls_name)}{COLON_COLOR}:{RESET}{RIGHT_COLOR}{method_name}{RESET}"
                    print(colored)

    except ValueError as e:
        sys.stderr.write(f"{YELLOW}Validation Error:{RESET} {RED}{e}{RESET}\n")


if __name__ == "__main__":
    main()
