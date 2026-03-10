import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo


def convert_from_uk_to_utc(value: datetime | date) -> datetime:
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min)

    uk = ZoneInfo("Europe/London")
    utc = ZoneInfo("UTC")

    if value.tzinfo is None:
        value = value.replace(tzinfo=uk)
    return value.astimezone(utc)


def parse_date_yyyymmdd(v: str | date) -> date:
    if isinstance(v, date):
        return v
    v_str = str(v)
    if not re.fullmatch(r"\d{8}", v_str):
        msg = f"Invalid format: {v_str}. Must be YYYYMMDD."
        raise ValueError(msg)
    try:
        return datetime.strptime(v_str, "%Y%m%d").date()  # noqa: DTZ007
    except ValueError as err:
        msg = f"Invalid date value: {v_str}."
        raise ValueError(msg) from err


def parse_time_hhmmss(v: str | time | None) -> time | None:
    if not v:
        return None
    if isinstance(v, time):
        return v
    v_str = str(v).strip()
    if re.fullmatch(r"^\d{2}:\d{2}:\d{2}$", v_str):
        try:
            return datetime.strptime(v_str, "%H:%M:%S").time()  # noqa: DTZ007
        except ValueError as err:
            msg = f"Invalid time value: {v_str}."
            raise ValueError(msg) from err
    msg = f"Invalid format: {v_str}. Must be HH:MM:SS."
    raise ValueError(msg)
