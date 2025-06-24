import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Constants
OUTPUT_ROOT = "out"
DATE_FORMAT = "%Y%m%d"
VAR_PATTERN = re.compile(r"<<([^<>]+)>>")

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


class DateVariableResolver:
    """Handles the logic for parsing and evaluating date-based variables."""

    def __init__(self, today: datetime = None):
        self.today = today or datetime.today()

    def resolve(self, token: str) -> str:
        logging.debug(f"Resolving variable: {token}")
        parts = token.split("_")
        if len(parts) < 3 or parts[0].upper() != "DATE":
            raise ValueError(f"Unsupported variable format: {token}")

        _, unit, value = parts[0], parts[1].lower(), parts[2]

        try:
            offset = int(value)
        except ValueError:
            raise ValueError(f"Invalid offset value: {value}")

        if unit == "day":
            return (self.today + timedelta(days=offset)).strftime(DATE_FORMAT)
        if unit == "week":
            return (self.today + timedelta(weeks=offset)).strftime(DATE_FORMAT)
        if unit == "year":
            return (self.today.replace(year=self.today.year + offset)).strftime(DATE_FORMAT)
        if unit == "age":
            try:
                birth_date = self.today.replace(year=self.today.year - offset)
            except ValueError:
                # Handle February 29th
                birth_date = self.today.replace(month=2, day=28, year=self.today.year - offset)
            return birth_date.strftime(DATE_FORMAT)
        raise ValueError(f"Unsupported calculation unit: {unit}")


class JsonTestDataProcessor:
    """Processes JSON test files by resolving placeholders in 'data' arrays."""

    def __init__(self, input_dir: Path, output_dir: Path, resolver: DateVariableResolver):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.resolver = resolver

    def resolve_placeholders(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self.resolve_placeholders(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.resolve_placeholders(item) for item in obj]
        if isinstance(obj, str):
            return VAR_PATTERN.sub(self._replace_token, obj)
        return obj

    def _replace_token(self, match: re.Match) -> str:
        token = match.group(1)
        try:
            return self.resolver.resolve(token)
        except Exception as e:
            logging.warning(f"Failed to resolve variable {token}: {e}")
            return match.group(0)

    def process_file(self, file_path: Path):
        logging.info(f"Processing file: {file_path}")
        try:
            with open(file_path) as f:
                content = json.load(f)
        except Exception as e:
            logging.exception(f"Failed to read {file_path}: {e}")
            return

        try:
            resolved = self.resolve_placeholders(content)
        except Exception as e:
            logging.exception(f"Failed to resolve placeholders: {e}")
            return

        if "data" not in resolved:
            logging.error(f"Missing 'data' key in {file_path}")
            return

        relative_path = file_path.relative_to(self.input_dir)
        output_path = self.output_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, "w") as f:
                json.dump(resolved["data"], f, indent=2)
            logging.info(f"Written resolved file: {output_path}")
        except Exception as e:
            logging.exception(f"Failed to write output: {e}")


def main():
    input_dir = Path()
    output_dir = Path(OUTPUT_ROOT)
    resolver = DateVariableResolver()

    processor = JsonTestDataProcessor(input_dir, output_dir, resolver)

    logging.info(f"Scanning for JSON files in {input_dir}")
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".json"):
                processor.process_file(Path(root) / file)
            else:
                logging.debug(f"Skipping non-JSON file: {file}")


if __name__ == "__main__":
    main()
