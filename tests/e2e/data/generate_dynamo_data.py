import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

OUTPUT_ROOT = "out"
DATE_FORMAT = "%Y%m%d"
VAR_PATTERN = re.compile(r"<<([^<>]+)>>")
REQUIRED_TOKEN_PARTS = 3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


class DateVariableResolver:
    def __init__(self, today: datetime | None = None):
        self.today = today or datetime.now(tz=timezone.UTC)

    def resolve(self, token: str) -> str:
        logger.debug("Resolving variable: %s", token)
        parts = token.split("_")
        if len(parts) < REQUIRED_TOKEN_PARTS or parts[0].upper() != "DATE":
            msg = f"Unsupported variable format: {token}"
            raise ValueError(msg)
        _, unit, value = parts[0], parts[1].lower(), parts[2]
        try:
            offset = int(value)
        except ValueError as err:
            msg = f"Invalid offset value: {value}"
            raise ValueError(msg) from err
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
                birth_date = self.today.replace(month=2, day=28, year=self.today.year - offset)
            return birth_date.strftime(DATE_FORMAT)
        msg = f"Unsupported calculation unit: {unit}"
        raise ValueError(msg)


class JsonTestDataProcessor:
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
        except ValueError:
            logger.warning("Failed to resolve variable: %s", token)
            return match.group(0)

    def process_file(self, file_path: Path):
        logger.info("Processing file: %s", file_path)
        try:
            with file_path.open() as f:
                content = json.load(f)
        except Exception:
            logger.exception("Failed to read file: %s", file_path)
            return
        try:
            resolved = self.resolve_placeholders(content)
        except Exception:
            logger.exception("Failed to resolve placeholders in file: %s", file_path)
            return
        if "data" not in resolved:
            logger.error("Missing 'data' key in file: %s", file_path)
            return
        relative_path = file_path.relative_to(self.input_dir)
        output_path = self.output_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_path.open("w") as f:
                json.dump(resolved["data"], f, indent=2)
            logger.info("Written resolved file: %s", output_path)
        except Exception:
            logger.exception("Failed to write output to: %s", output_path)


def main():
    input_dir = Path()
    output_dir = Path(OUTPUT_ROOT)
    resolver = DateVariableResolver()
    processor = JsonTestDataProcessor(input_dir, output_dir, resolver)
    logger.info("Scanning for JSON files in directory: %s", input_dir)
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = Path(root) / file
            if file.endswith(".json"):
                processor.process_file(file_path)
            else:
                logger.debug("Skipping non-JSON file: %s", file)


if __name__ == "__main__":
    main()
