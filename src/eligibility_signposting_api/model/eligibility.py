from dataclasses import dataclass
from datetime import date
from enum import Enum, auto
from typing import NewType

NHSNumber = NewType("NHSNumber", str)
DateOfBirth = NewType("DateOfBirth", date)
Postcode = NewType("Postcode", str)


class Status(Enum):
    not_eligible = auto()
    not_actionable = auto()
    actionable = auto()


@dataclass
class Condition:
    condition: str
    status: Status


@dataclass
class EligibilityStatus:
    conditions: list[Condition]
