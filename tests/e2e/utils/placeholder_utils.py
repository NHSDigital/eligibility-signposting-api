import logging
import re
from calendar import isleap
from datetime import UTC, datetime, timedelta

from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


def resolve_placeholders(value, context=None, file_name=None):
    if not isinstance(value, str):
        return value

    match = re.search(r"<<(.*?)>>", value)
    if not match:
        return value

    placeholder = match.group(1)

    try:
        resolved = _resolve_placeholder_value(placeholder)
        if context:
            context.add(placeholder, resolved, file_name)
        return value.replace(f"<<{placeholder}>>", resolved)
    except Exception:
        logger.exception("[ERROR] Could not resolve placeholder %s:", placeholder)
        return value


def _resolve_placeholder_value(placeholder: str) -> str:
    placeholder_parts_length = 3
    # RDATE
    valid_placeholder_types = ["DATE", "RDATE", "IGNORE"]
    result = f"<<{placeholder}>>"  # Default fallback

    if placeholder in ["IGNORE_RESPONSE_ID", "IGNORE_DATE"]:
        return placeholder

    parts = placeholder.split("_")
    if len(parts) != placeholder_parts_length or parts[0] not in valid_placeholder_types:
        return result

    today = datetime.now(UTC)
    date_type, arg = parts[1], parts[2]

    try:
        if date_type == "AGE":
            result = _resolve_age_placeholder(today, int(arg), parts[0])
        elif date_type == "DAY":
            result = _format_date(today + timedelta(days=int(arg)), parts[0])
        elif date_type == "WEEK":
            result = _format_date(today + timedelta(weeks=int(arg)), parts[0])
        elif date_type == "MONTH":
            result = _format_date(today + relativedelta(months=int(arg)), parts[0])
        elif date_type == "YEAR":
            result = _format_date(today + relativedelta(years=int(arg)), parts[0])
    except Exception:
        logger.exception("Failed to resolve placeholder: %s", placeholder)
        raise
    return result


def _resolve_age_placeholder(today: datetime, years_back: int, format_type: str) -> str:
    target_year = today.year - years_back
    february = 2
    leap_year_day = 29
    try:
        result_date = today.replace(year=target_year)
    except ValueError:
        if today.month == february and today.day == leap_year_day and not isleap(target_year):
            result_date = datetime(target_year, 2, 28, tzinfo=UTC)
        else:
            raise
    return _format_date(result_date, format_type)


def _format_date(date: datetime, format_type: str) -> str:
    return date.strftime("%Y%m%d") if format_type == "DATE" else date.strftime("%-d %B %Y")
