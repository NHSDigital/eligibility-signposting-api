from __future__ import annotations

import json
import re
import typing
from collections import Counter
from datetime import UTC, date, datetime
from enum import StrEnum
from functools import cached_property
from operator import attrgetter
from typing import Literal, NewType

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    PrivateAttr,
    RootModel,
    field_serializer,
    field_validator,
    model_validator,
)

from eligibility_signposting_api.config.constants import ALLOWED_CONDITIONS, RULE_STOP_DEFAULT

if typing.TYPE_CHECKING:  # pragma: no cover
    from pydantic import SerializationInfo

CampaignName = NewType("CampaignName", str)
CampaignVersion = NewType("CampaignVersion", int)
CampaignID = NewType("CampaignID", str)
IterationName = NewType("IterationName", str)
IterationVersion = NewType("IterationVersion", int)
IterationID = NewType("IterationID", str)
IterationDate = NewType("IterationDate", date)
RuleName = NewType("RuleName", str)
RuleDescription = NewType("RuleDescription", str)
RulePriority = NewType("RulePriority", int)
RuleAttributeName = NewType("RuleAttributeName", str)
RuleAttributeTarget = NewType("RuleAttributeTarget", str)
RuleComparator = NewType("RuleComparator", str)
StartDate = NewType("StartDate", date)
EndDate = NewType("EndDate", date)
CohortLabel = NewType("CohortLabel", str)
CohortGroup = NewType("CohortGroup", str)
Description = NewType("Description", str)
RuleStop = NewType("RuleStop", bool)
CommsRouting = NewType("CommsRouting", str)
RuleCode = NewType("RuleCode", str)
RuleText = NewType("RuleText", str)


class RuleType(StrEnum):
    filter = "F"
    suppression = "S"
    redirect = "R"
    not_eligible_actions = "X"
    not_actionable_actions = "Y"


class RuleOperator(StrEnum):
    equals = "="
    gt = ">"
    lt = "<"
    ne = "!="
    gte = ">="
    lte = "<="
    contains = "contains"
    not_contains = "not_contains"
    starts_with = "starts_with"
    not_starts_with = "not_starts_with"
    ends_with = "ends_with"
    is_in = "in"
    not_in = "not_in"
    member_of = "MemberOf"
    not_member_of = "NotaMemberOf"
    is_null = "is_null"
    is_not_null = "is_not_null"
    is_between = "between"
    is_not_between = "not_between"
    is_empty = "is_empty"
    is_not_empty = "is_not_empty"
    is_true = "is_true"
    is_false = "is_false"
    day_lte = "D<="
    day_lt = "D<"
    day_gte = "D>="
    day_gt = "D>"
    week_lte = "W<="
    week_lt = "W<"
    week_gte = "W>="
    week_gt = "W>"
    year_lte = "Y<="
    year_lt = "Y<"
    year_gte = "Y>="
    year_gt = "Y>"


class RuleAttributeLevel(StrEnum):
    PERSON = "PERSON"
    TARGET = "TARGET"
    COHORT = "COHORT"


class Virtual(StrEnum):
    YES = "Y"
    NO = "N"


class IterationCohort(BaseModel):
    cohort_label: CohortLabel = Field(alias="CohortLabel")
    cohort_group: CohortGroup = Field(alias="CohortGroup")
    positive_description: Description | None = Field(None, alias="PositiveDescription")
    negative_description: Description | None = Field(None, alias="NegativeDescription")
    priority: int | None = Field(None, alias="Priority")
    virtual: Virtual = Field(default=Virtual.NO, alias="Virtual")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @cached_property
    def is_virtual_cohort(self) -> bool:
        return self.virtual == Virtual.YES

    @field_validator("virtual", mode="before")
    @classmethod
    def normalize_virtual(cls, value: str) -> Virtual:
        if value is None:
            return Virtual.NO
        if isinstance(value, str):
            value = value.strip().upper()
        if value == "Y":
            return Virtual.YES
        if value == "N":
            return Virtual.NO
        msg = f"Invalid value for Virtual: {value!r}"
        raise ValueError(msg)


class IterationRule(BaseModel):
    type: RuleType = Field(..., alias="Type")
    name: RuleName = Field(..., alias="Name")
    code: RuleCode | None = Field(None, alias="Code", description="use `rule_code` property instead.")
    description: RuleDescription = Field(..., alias="Description", description="use `rule_text` property instead.")
    priority: RulePriority = Field(..., alias="Priority")
    attribute_level: RuleAttributeLevel = Field(..., alias="AttributeLevel")
    attribute_name: RuleAttributeName | None = Field(None, alias="AttributeName")
    cohort_label: CohortLabel | None = Field(
        None,
        alias="CohortLabel",
        description="Raw label input. Prefer using `parsed_cohort_labels` for normalized access.",
    )
    operator: RuleOperator = Field(..., alias="Operator")
    comparator: RuleComparator = Field(..., alias="Comparator")
    attribute_target: RuleAttributeTarget | None = Field(None, alias="AttributeTarget")
    rule_stop: RuleStop = Field(RuleStop(RULE_STOP_DEFAULT), alias="RuleStop")
    comms_routing: CommsRouting | None = Field(None, alias="CommsRouting")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @field_validator("rule_stop", mode="before")
    def parse_yn_to_bool(cls, v: str | bool) -> bool:  # noqa: N805, FBT001
        if isinstance(v, str):
            return v.upper() == "Y"
        return v

    _parent: Iteration | None = PrivateAttr(default=None)

    def set_parent(self, parent: Iteration) -> None:
        self._parent = parent

    @property
    def rule_code(self) -> str:
        """
        Resolves the rule code using the parent Iteration's rules_mapper.

        If the rule name matches any entry in the rules_mapper, the corresponding
        rule_code is returned.

        If no match is found, rule code is returned if it exists, otherwise the rule name is returned.
        """
        rule_code = None
        if self._parent and self._parent.rules_mapper:
            for rule_entry in self._parent.rules_mapper.values():
                if rule_entry and self.name in rule_entry.rule_names:
                    rule_code = rule_entry.rule_code
        return rule_code or self.code or self.name

    @property
    def rule_text(self) -> str:
        """
        Resolves the rule text using the parent Iteration's rules_mapper.

        If the rule name matches any entry in the rules_mapper, the corresponding
        rule_text is returned.

        If no match is found, the rule description is returned.
        """
        rule_text = None
        if self._parent and self._parent.rules_mapper:
            for rule_entry in self._parent.rules_mapper.values():
                if rule_entry and self.name in rule_entry.rule_names:
                    rule_text = rule_entry.rule_text
        return rule_text or self.description

    @cached_property
    def parsed_cohort_labels(self) -> list[str]:
        """
        Parses the cohort_label string into a list of individual labels.

        Returns:
            A list of cohort labels, split by comma. If no label is set, returns an empty list.
        """
        if not self.cohort_label:
            return []
        return [label.strip() for label in self.cohort_label.split(",") if label.strip()]

    def __str__(self) -> str:
        return json.dumps(self.model_dump(by_alias=True), indent=2)


class AvailableAction(BaseModel):
    action_type: str = Field(..., alias="ActionType")
    action_code: str = Field(..., alias="ExternalRoutingCode")
    action_description: str | None = Field(None, alias="ActionDescription")
    url_link: HttpUrl | None = Field(None, alias="UrlLink")
    url_label: str | None = Field(None, alias="UrlLabel")

    model_config = {"populate_by_name": True}


class ActionsMapper(RootModel[dict[str, AvailableAction]]):
    def get(self, key: str, default: AvailableAction | None = None) -> AvailableAction | None:
        return self.root.get(key, default)


class StatusText(BaseModel):
    not_eligible: str | None = Field(None, alias="NotEligible")
    not_actionable: str | None = Field(None, alias="NotActionable")
    actionable: str | None = Field(None, alias="Actionable")

    model_config = {"populate_by_name": True}


class RuleEntry(BaseModel):
    rule_names: list[RuleName] = Field(..., alias="RuleNames")
    rule_code: RuleCode | None = Field(None, alias="RuleCode")
    rule_text: RuleText | None = Field(None, alias="RuleText")

    model_config = {"populate_by_name": True}


class RulesMapper(RootModel[dict[str, RuleEntry]]):
    def get(self, key: str, default: RuleEntry | None = None) -> RuleEntry | None:
        return self.root.get(key, default)

    def values(self) -> list[RuleEntry]:
        return list(self.root.values())


class Iteration(BaseModel):
    id: IterationID = Field(..., alias="ID")
    version: IterationVersion = Field(..., alias="Version")
    name: IterationName = Field(..., alias="Name")
    iteration_date: IterationDate = Field(..., alias="IterationDate")
    iteration_number: int | None = Field(None, alias="IterationNumber")
    approval_minimum: int | None = Field(None, alias="ApprovalMinimum")
    approval_maximum: int | None = Field(None, alias="ApprovalMaximum")
    type: Literal["A", "M", "S", "O"] = Field(..., alias="Type")
    default_comms_routing: str = Field(..., alias="DefaultCommsRouting")
    default_not_eligible_routing: str = Field(..., alias="DefaultNotEligibleRouting")
    default_not_actionable_routing: str = Field(..., alias="DefaultNotActionableRouting")
    iteration_cohorts: list[IterationCohort] = Field(..., alias="IterationCohorts")
    iteration_rules: list[IterationRule] = Field(..., alias="IterationRules")
    actions_mapper: ActionsMapper = Field(..., alias="ActionsMapper")
    rules_mapper: RulesMapper | None = Field(None, alias="RulesMapper")
    status_text: StatusText | None = Field(None, alias="StatusText")

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True, "extra": "ignore"}

    @field_validator("iteration_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | date) -> date:
        if isinstance(v, date):
            return v

        v_str = str(v)

        if not re.fullmatch(r"\d{8}", v_str):
            msg = f"Invalid format: {v_str}. Must be YYYYMMDD with 8 digits."
            raise ValueError(msg)

        try:
            return datetime.strptime(v_str, "%Y%m%d").date()  # noqa: DTZ007
        except ValueError as err:
            msg = f"Invalid date value: {v_str}. Must be a valid calendar date in YYYYMMDD format."
            raise ValueError(msg) from err

    @field_serializer("iteration_date", when_used="always")
    @staticmethod
    def serialize_dates(v: date, _info: SerializationInfo) -> str:
        return v.strftime("%Y%m%d")

    @model_validator(mode="after")
    def attach_rule_parents(self) -> Iteration:
        for rule in self.iteration_rules:
            rule.set_parent(self)
        return self

    def __str__(self) -> str:
        return json.dumps(self.model_dump(by_alias=True), indent=2)


class CampaignConfig(BaseModel):
    id: CampaignID = Field(..., alias="ID")
    version: CampaignVersion = Field(..., alias="Version")
    name: CampaignName = Field(..., alias="Name")
    type: Literal["V", "S"] = Field(..., alias="Type")
    target: ALLOWED_CONDITIONS = Field(..., alias="Target")
    manager: list[str] | None = Field(None, alias="Manager")
    approver: list[str] | None = Field(None, alias="Approver")
    reviewer: list[str] | None = Field(None, alias="Reviewer")
    iteration_frequency: Literal["X", "D", "W", "M", "Q", "A"] = Field(..., alias="IterationFrequency")
    iteration_type: Literal["A", "M", "S", "O"] = Field(..., alias="IterationType")
    iteration_time: str | None = Field(None, alias="IterationTime")
    default_comms_routing: str | None = Field(None, alias="DefaultCommsRouting")
    start_date: StartDate = Field(..., alias="StartDate")
    end_date: EndDate = Field(..., alias="EndDate")
    approval_minimum: int | None = Field(None, alias="ApprovalMinimum")
    approval_maximum: int | None = Field(None, alias="ApprovalMaximum")
    iterations: list[Iteration] = Field(..., min_length=1, alias="Iterations")

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True, "extra": "ignore"}

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | date) -> date:
        if isinstance(v, date):
            return v

        v_str = str(v)

        if not re.fullmatch(r"\d{8}", v_str):
            msg = f"Invalid format: {v_str}. Must be YYYYMMDD with 8 digits."
            raise ValueError(msg)

        try:
            return datetime.strptime(v_str, "%Y%m%d").date()  # noqa: DTZ007
        except ValueError as err:
            msg = f"Invalid date value: {v_str}. Must be a valid calendar date in YYYYMMDD format."
            raise ValueError(msg) from err

    @field_serializer("start_date", "end_date", when_used="always")
    @staticmethod
    def serialize_dates(v: date, _info: SerializationInfo) -> str:
        return v.strftime("%Y%m%d")

    @model_validator(mode="after")
    def check_start_and_end_dates_sensible(self) -> typing.Self:
        if self.start_date > self.end_date:
            message = f"start date {self.start_date} after end date {self.end_date}"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def check_no_overlapping_iterations(self) -> typing.Self:
        iterations_by_date = Counter([i.iteration_date for i in self.iterations])
        if multiple_found := next(((d, c) for d, c in iterations_by_date.most_common() if c > 1), None):
            iteration_date, count = multiple_found
            message = f"{count} iterations with iteration date {iteration_date} in campaign {self.id}"
            raise ValueError(message)
        return self

    @cached_property
    def campaign_live(self) -> bool:
        today = datetime.now(tz=UTC).date()
        return self.start_date <= today <= self.end_date

    @cached_property
    def current_iteration(self) -> Iteration:
        today = datetime.now(tz=UTC).date()
        iterations_by_date_descending = sorted(self.iterations, key=attrgetter("iteration_date"), reverse=True)
        return next(i for i in iterations_by_date_descending if i.iteration_date <= today)

    def __str__(self) -> str:
        return json.dumps(self.model_dump(by_alias=True), indent=2)


class Rules(BaseModel):
    """Eligibility rules.

    This is a Pydantic model, into which we can de-serialise rules stored in DPS's format."""

    campaign_config: CampaignConfig = Field(..., alias="CampaignConfig")

    model_config = {"populate_by_name": True, "extra": "ignore"}
