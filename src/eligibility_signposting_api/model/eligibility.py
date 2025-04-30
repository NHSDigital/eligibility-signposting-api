from dataclasses import dataclass
from datetime import date
from enum import Enum, auto
from typing import NewType

NHSNumber = NewType("NHSNumber", str)
DateOfBirth = NewType("DateOfBirth", date)
Postcode = NewType("Postcode", str)
ConditionName = NewType("ConditionName", str)

RuleName = NewType("RuleName", str)
RuleResult = NewType("RuleResult", str)


class RuleType(str, Enum):
    filter = "F"
    suppression = "S"
    redirect = "R"


class Status(Enum):
    not_eligible = auto()
    not_actionable = auto()
    actionable = auto()


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
