import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import UTC, datetime
from operator import attrgetter
from pathlib import Path

from pydantic import ValidationError

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
BLUE = "\033[34m"


def refine_error(e: ValidationError) -> str:
    """Return a very short, single-line error message."""
    lines = [f"❌Validation Error: {len(e.errors())} validation error(s)"]

    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        type_ = err["type"]

        lines.append(f"{loc} : {msg} [type={type_}]")

    return "\n".join(lines)


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Validate campaign configuration.")
    parser.add_argument("--config_path", required=True, help="Path to the campaign config JSON file")
    args = parser.parse_args()

    try:
        with Path(args.config_path).open() as file:
            json_data = json.load(file)
            result = RulesValidation(**json_data)
            sys.stdout.write(f"{GREEN}Valid Config{RESET}\n")

            display_current_iteration(result)

            # Group by class
            grouped = defaultdict(list)
            for v in VALIDATORS_CALLED:
                cls, method = v.split(":", 1)
                grouped[cls].append(method.strip())

            # Print grouped
            for cls_name in sorted(grouped.keys(), reverse=True):
                methods = sorted(grouped[cls_name])
                # First method prints class name
                first = methods[0]
                colored = f"{BLUE}{cls_name}{RESET}{YELLOW}:{RESET}{GREEN}{first}{RESET}\n"
                sys.stdout.write(colored)
                # Rest methods indented
                for method_name in methods[1:]:
                    colored = f"{' ' * len(cls_name)}{YELLOW}:{RESET}{GREEN}{method_name}{RESET}\n"
                    sys.stdout.write(colored)

    except ValidationError as e:
        clean = refine_error(e)
        sys.stderr.write(f"{YELLOW}{clean}{RESET}\n")


def display_current_iteration(result: RulesValidation) -> None:
    config = result.campaign_config
    iterations = config.iterations
    is_campaign_live = config.campaign_live
    today = datetime.now(tz=UTC).date()

    no_of_iterations = len(iterations)
    is_campaign_expired = config.end_date < today

    # ---- Current Iteration ----
    if is_campaign_live:
        sys.stdout.write(f"{YELLOW}Campaign is {RESET}{GREEN}LIVE{RESET}\n")
        current = config.current_iteration
        if current:
            sys.stdout.write(
                f"{YELLOW}Current active Iteration Number: {RESET}{GREEN}{current.iteration_number}{RESET}\n"
            )
            sys.stdout.write(
                f"{YELLOW}Current active Iteration's date&time: {RESET}{GREEN}{current.iteration_datetime}{RESET}\n"
            )
        else:
            sys.stdout.write(f"{YELLOW}No active iteration could be determined{RESET}\n")

    else:
        sys.stdout.write(f"{YELLOW}Campaign is {RESET}{GREEN}NOT LIVE{RESET} ")

        if is_campaign_expired:
            sys.stdout.write(f"{YELLOW}[EXPIRED on {config.end_date}]{RESET}\n")
        else:
            sys.stdout.write(f"{YELLOW}[To be STARTED on {RESET}{GREEN}{config.start_date}{RESET}{YELLOW}]{RESET}\n")

    # ---- Next Iteration ----
    if not is_campaign_expired:
        sorted_iterations = sorted(iterations, key=attrgetter("iteration_date"))
        next_iteration = next(
            (i for i in sorted_iterations if i.iteration_date > today), None
        )

        if next_iteration:
            sys.stdout.write(
                f"{YELLOW}Next active Iteration Number: {RESET}{GREEN}{next_iteration.iteration_number}{RESET}\n"
            )
            sys.stdout.write(
                f"{YELLOW}Next active Iteration's date&time: {RESET}{GREEN}{next_iteration.iteration_datetime}{RESET}\n"
            )
        else:
            sys.stdout.write(f"{YELLOW}No next active iteration could be determined{RESET}\n")

    # ---- Total Iterations ----
    sys.stdout.write(
        f"{YELLOW}Total iterations configured: {RESET}{GREEN}{no_of_iterations}{RESET}\n"
    )

if __name__ == "__main__":  # pragma: no cover
    main()
