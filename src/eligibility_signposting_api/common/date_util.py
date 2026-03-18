import re
from collections.abc import Callable
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

UK_TIMEZONE = ZoneInfo("Europe/London")


def now_uk() -> datetime:
    return datetime.now(tz=UK_TIMEZONE)


def date_with_uk_timezone(parsed_date: date) -> date:
    return datetime.combine(parsed_date, time.min).replace(tzinfo=UK_TIMEZONE).date()


def datetime_with_uk_timezone(parsed_date_time: datetime) -> datetime:
    return parsed_date_time.replace(tzinfo=UK_TIMEZONE)


def _parse_with_format[T](
    value: str,
    regex: str,
    fmt: str,
    error_info: tuple[str, str],
    transform: Callable[[datetime], T],
) -> T:
    """Shared logic for regex validation and datetime parsing."""
    label, expected_format = error_info

    if not re.fullmatch(regex, value):
        msg = f"Invalid format: {value}. Must be {expected_format}."
        raise ValueError(msg)
    try:
        dt = datetime.strptime(value, fmt)  # noqa: DTZ007
        return transform(dt)
    except ValueError as err:
        msg = f"Invalid {label} value: {value}."
        raise ValueError(msg) from err


def parse_date_yyyymmdd(v: str | date) -> date:
    if isinstance(v, date):
        return v
    # Pass the last two strings as a single tuple inside parentheses
    return _parse_with_format(str(v), r"\d{8}", "%Y%m%d", ("date", "YYYYMMDD"), lambda dt: dt.date())


def parse_time_hhmmss(v: str | time | None) -> time | None:
    if v is None:
        return None
    if isinstance(v, time):
        return v
    # Pass the last two strings as a single tuple inside parentheses
    return _parse_with_format(
        str(v).strip(), r"^\d{2}:\d{2}:\d{2}$", "%H:%M:%S", ("time", "HH:MM:SS"), lambda dt: dt.time()
    )
