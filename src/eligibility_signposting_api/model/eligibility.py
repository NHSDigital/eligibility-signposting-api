from dataclasses import dataclass
from datetime import date
from enum import Enum, StrEnum, auto
from functools import total_ordering
from typing import NewType, Self

NHSNumber = NewType("NHSNumber", str)
DateOfBirth = NewType("DateOfBirth", date)
Postcode = NewType("Postcode", str)
ConditionName = NewType("ConditionName", str)

RuleName = NewType("RuleName", str)
RuleResult = NewType("RuleResult", str)


class RuleType(StrEnum):
    filter = "F"
    suppression = "S"
    redirect = "R"


@total_ordering
class Status(Enum):
    not_eligible = auto()
    not_actionable = auto()
    actionable = auto()

    def __lt__(self, other: Self) -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


@dataclass
class Reason:
    rule_type: RuleType
    rule_name: RuleName
    rule_result: RuleResult


@dataclass
class Condition:
    condition_name: ConditionName
    status: Status
    reasons: list[Reason]


@dataclass
class EligibilityStatus:
    """Represents a person's eligibility for vaccination."""

    conditions: list[Condition]
