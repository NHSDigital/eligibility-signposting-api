import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import isleap


def resolve_placeholders(value, context=None, file_name=None):
    if not isinstance(value, str):
        return value

    match = re.search(r"<<(.*?)>>", value)
    if not match:
        return value  # No placeholder to resolve

    placeholder = match.group(1)
    parts = placeholder.split("_")

    try:
        if placeholder in ["IGNORE_RESPONSE_ID", "IGNORE_DATE"]:
            return value.replace(f"<<{placeholder}>>", placeholder)
        elif len(parts) != 3 or parts[0] not in ["DATE", "RDATE", "IGNORE"]:
            return value  # Unrecognized format

        date_type, arg = parts[1], parts[2]
        today = datetime.today()

        if date_type == "AGE":
            target_year = today.year - int(arg)
            try:
                result_date = today.replace(year=target_year)
            except ValueError:
                if today.month == 2 and today.day == 29 and not isleap(target_year):
                    result_date = datetime(target_year, 2, 28)
                else:
                    raise

        elif date_type == "DAY":
            result_date = today + timedelta(days=int(arg))

        elif date_type == "MONTH":
            result_date = today + relativedelta(months=int(arg))

        elif date_type == "YEAR":
            result_date = today + relativedelta(years=int(arg))

        else:
            return value

        resolved = result_date.strftime("%Y%m%d") if parts[0] == "DATE" else result_date.strftime("%-d %B %Y")

        if context:
            context.add(placeholder, resolved, file_name)

        # Replace the single placeholder in the original string
        return value.replace(f"<<{placeholder}>>", resolved)

    except Exception as e:
        print(f"[ERROR] Could not resolve placeholder '{placeholder}': {e}")
        return value
