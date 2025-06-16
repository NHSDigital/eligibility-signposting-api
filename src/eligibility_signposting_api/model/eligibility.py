from __future__ import annotations

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

    @property
    def is_exclusion(self) -> bool:
        return self is not Status.actionable

    @staticmethod
    def worst(*statuses: Status) -> Status:
        """Pick the worst status from those given.

        Here "worst" means furthest from being able to access vaccination, so not-eligible is "worse" than
        not-actionable, and not-actionable is "worse" than actionable.
        """
        return min(statuses)

    @staticmethod
    def best(*statuses: Status) -> Status:
        """Pick the best status between the existing status, and the status implied by
        the rule excluding the person from vaccination.

        Here "best" means closest to being able to access vaccination, so not-actionable is "better" than
        not-eligible, and actionable is "better" than not-actionable.
        """
        return max(statuses)


@dataclass
class Reason:
    rule_type: RuleType
    rule_name: RuleName
    rule_result: RuleResult
    matcher_matched: bool

#TODO: create types
@dataclass
class Action:
    actionType: str
    actionCode: str
    actionDescription: str
    urlLink: str
    urlLabel: str

@dataclass
class Condition:
    condition_name: ConditionName
    status: Status
    cohort_results: list[CohortResult]
    actions: list[Action]

@dataclass
class CohortResult:
    cohort_code: str
    status: Status
    reasons: list[Reason]
    description: str


@dataclass
class IterationResult:
    status: Status
    cohort_results: list[CohortResult]


@dataclass
class EligibilityStatus:
    """Represents a person's eligibility for vaccination."""

    conditions: list[Condition]
