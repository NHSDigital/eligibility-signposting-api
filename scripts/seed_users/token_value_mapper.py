from datetime import datetime
import random

today = datetime.today()

token_to_value = {
    "DATE_AGE_45": lambda: today.replace(year=today.year - 45).strftime("%Y%m%d"),
    "DATE_AGE_50": lambda: today.replace(year=today.year - 50).strftime("%Y%m%d"),
    "DATE_AGE_74": lambda: today.replace(year=today.year - 74).strftime("%Y%m%d"),
    "DATE_AGE_75": lambda: today.replace(year=today.year - 75).strftime("%Y%m%d"),
    "DATE_AGE_80": lambda: today.replace(year=today.year - 80).strftime("%Y%m%d"),
    "DATE_AGE_75_89": lambda: datetime(
        year=today.year - random.randint(75, 89),
        month=random.randint(1, 12),
        day=random.randint(1, 28)
    ).strftime("%Y%m%d")
}
