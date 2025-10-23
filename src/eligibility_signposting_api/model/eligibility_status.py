from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum, StrEnum, auto
from functools import total_ordering
from typing import TYPE_CHECKING, NewType, Self

from pydantic import HttpUrl

if TYPE_CHECKING:
    from eligibility_signposting_api.model import campaign_config
    from eligibility_signposting_api.model.campaign_config import CampaignID, CampaignVersion, CohortLabel, Iteration

NHSNumber = NewType("NHSNumber", str)
DateOfBirth = NewType("DateOfBirth", date)
Postcode = NewType("Postcode", str)
ConditionName = NewType("ConditionName", str)

RuleName = NewType("RuleName", str)
RuleCode = NewType("RuleCode", str)
RuleText = NewType("RuleDescription", str)
RulePriority = NewType("RulePriority", str)

InternalActionCode = NewType("InternalActionCode", str)
ActionType = NewType("ActionType", str)
ActionCode = NewType("ActionCode", str)
ActionDescription = NewType("ActionDescription", str)
UrlLink = NewType("UrlLink", HttpUrl)
UrlLabel = NewType("UrlLabel", str)

StatusText = NewType("StatusText", str)


class RuleType(StrEnum):
    filter = "F"
    suppression = "S"
    redirect = "R"
    not_eligible_actions = "X"
    not_actionable_actions = "Y"


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

    def get_default_status_text(self, condition_name: ConditionName) -> StatusText:
        status_to_text_mapping = {
            self.not_eligible: lambda: StatusText("We do not believe you can have it"),
            self.not_actionable: lambda: StatusText(f"You should have the {condition_name} vaccine"),
            self.actionable: lambda: StatusText(f"You should have the {condition_name} vaccine"),
        }
        return status_to_text_mapping.get(self, lambda: StatusText("Unknown status provided"))()

    def get_action_rule_type(self) -> RuleType:
        return {
            self.not_eligible: RuleType.not_eligible_actions,
            self.not_actionable: RuleType.not_actionable_actions,
            self.actionable: RuleType.redirect,
        }[self]


@dataclass
class Reason:
    rule_type: RuleType
    rule_name: RuleName
    rule_code: RuleCode
    rule_priority: RulePriority
    rule_text: RuleText | None
    matcher_matched: bool


@dataclass
class SuggestedAction:
    action_type: ActionType
    action_code: ActionCode
    action_description: ActionDescription | None
    url_link: UrlLink | None
    url_label: UrlLabel | None
    internal_action_code: InternalActionCode | None = None


@dataclass
class Condition:
    condition_name: ConditionName
    status: Status
    cohort_results: list[CohortGroupResult]
    suitability_rules: list[Reason]
    status_text: StatusText
    actions: list[SuggestedAction] | None = None


@dataclass
class CohortGroupResult:
    cohort_code: str
    status: Status
    reasons: list[Reason]
    description: str | None
    audit_rules: list[Reason]


@dataclass
class IterationResult:
    status: Status
    status_text: StatusText
    cohort_results: list[CohortGroupResult]
    actions: list[SuggestedAction] | None


@dataclass
class BestIterationResult:
    iteration_result: IterationResult
    active_iteration: Iteration | None = None
    campaign_id: CampaignID | None = None
    campaign_version: CampaignVersion | None = None
    cohort_results: dict[CohortLabel, CohortGroupResult] | None = None


@dataclass
class MatchedActionDetail:
    rule_name: campaign_config.RuleName | None = None
    rule_priority: campaign_config.RulePriority | None = None
    actions: list[SuggestedAction] | None = None


@dataclass
class EligibilityStatus:
    """Represents a person's eligibility for vaccination."""

    conditions: list[Condition]
