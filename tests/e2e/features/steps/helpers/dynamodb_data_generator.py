import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DATE_FORMAT = "%Y%m%d"
VAR_PATTERN = re.compile(r"<<([^<>]+)>>")
REQUIRED_TOKEN_PARTS = 3
logger = logging.getLogger(__name__)


class DateVariableResolver:
    def __init__(self, today: datetime | None = None):
        self.today = today or datetime.now(tz=UTC)

    def resolve(self, token: str) -> str:
        parts = token.split("_")
        if len(parts) < REQUIRED_TOKEN_PARTS or parts[0].upper() != "DATE":
            msg = f"Unsupported variable format: {token}"
            raise ValueError(msg)
        unit = parts[1].lower()
        try:
            offset = int(parts[2])
        except ValueError as e:
            msg = f"Invalid offset value: {parts[2]}"
            raise ValueError(msg) from e
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
        msg = f"Unsupported unit: {unit}"
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
        # logger.info("Processing file: %s", file_path)
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
            # logger.info("Written resolved file: %s", output_path)
        except Exception:
            logger.exception("Failed to write output to: %s", output_path)
