from __future__ import annotations

import json
import typing
from collections import Counter
from datetime import UTC, date, datetime
from enum import StrEnum
from functools import cached_property
from operator import attrgetter
from typing import Literal, NewType

from pydantic import BaseModel, Field, RootModel, field_serializer, field_validator, model_validator

from eligibility_signposting_api.config.contants import MAGIC_COHORT_LABEL, RULE_STOP_DEFAULT

if typing.TYPE_CHECKING:  # pragma: no cover
    from pydantic import SerializationInfo

CampaignName = NewType("CampaignName", str)
CampaignVersion = NewType("CampaignVersion", str)
CampaignID = NewType("CampaignID", str)
IterationName = NewType("IterationName", str)
IterationVersion = NewType("IterationVersion", str)
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


class RuleType(StrEnum):
    filter = "F"
    suppression = "S"
    redirect = "R"


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


class IterationCohort(BaseModel):
    cohort_label: CohortLabel = Field(alias="CohortLabel")
    cohort_group: CohortGroup = Field(alias="CohortGroup")
    positive_description: Description | None = Field(None, alias="PositiveDescription")
    negative_description: Description | None = Field(None, alias="NegativeDescription")
    priority: int | None = Field(None, alias="Priority")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @cached_property
    def is_magic_cohort(self) -> bool:
        return self.cohort_label.upper() == MAGIC_COHORT_LABEL.upper()


class IterationRule(BaseModel):
    type: RuleType = Field(..., alias="Type")
    name: RuleName = Field(..., alias="Name")
    description: RuleDescription = Field(..., alias="Description")
    priority: RulePriority = Field(..., alias="Priority")
    attribute_level: RuleAttributeLevel = Field(..., alias="AttributeLevel")
    attribute_name: RuleAttributeName | None = Field(None, alias="AttributeName")
    cohort_label: CohortLabel | None = Field(None, alias="CohortLabel")
    operator: RuleOperator = Field(..., alias="Operator")
    comparator: RuleComparator = Field(..., alias="Comparator")
    attribute_target: RuleAttributeTarget | None = Field(None, alias="AttributeTarget")
    rule_stop: RuleStop = Field(RuleStop(RULE_STOP_DEFAULT), alias="RuleStop")
    comms_routing: CommsRouting | None = Field(None, alias="CommsRouting")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @field_validator("rule_stop", mode="before")
    def parse_yn_to_bool(cls, v: str | bool) -> bool:  # noqa: N805
        if isinstance(v, str):
            return v.upper() == "Y"
        return v

    def __str__(self) -> str:
        return json.dumps(self.model_dump(by_alias=True), indent=2)


class AvailableAction(BaseModel):
    action_type: str = Field(..., alias="ActionType")
    action_code: str = Field(..., alias="ExternalRoutingCode")
    action_description: str | None = Field(None, alias="ActionDescription")
    url_link: str | None = Field(None, alias="UrlLink")
    url_label: str | None = Field(None, alias="UrlLabel")

    model_config = {"populate_by_name": True}


class ActionsMapper(RootModel[dict[str, AvailableAction]]):
    def get(self, key: str, default: AvailableAction | None = None) -> AvailableAction | None:
        return self.root.get(key, default)


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
    iteration_cohorts: list[IterationCohort] = Field(..., alias="IterationCohorts")
    iteration_rules: list[IterationRule] = Field(..., alias="IterationRules")
    actions_mapper: ActionsMapper = Field(..., alias="ActionsMapper")

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True, "extra": "ignore"}

    @field_validator("iteration_date", mode="before")
    @classmethod
    def parse_dates(cls, v: str | date) -> date:
        if isinstance(v, date):
            return v
        return datetime.strptime(v, "%Y%m%d").date()  # noqa: DTZ007

    @field_serializer("iteration_date", when_used="always")
    @staticmethod
    def serialize_dates(v: date, _info: SerializationInfo) -> str:
        return v.strftime("%Y%m%d")

    def __str__(self) -> str:
        return json.dumps(self.model_dump(by_alias=True), indent=2)


class CampaignConfig(BaseModel):
    id: CampaignID = Field(..., alias="ID")
    version: CampaignVersion = Field(..., alias="Version")
    name: CampaignName = Field(..., alias="Name")
    type: Literal["V", "S"] = Field(..., alias="Type")
    target: Literal["COVID", "FLU", "MMR", "RSV"] = Field(..., alias="Target")
    manager: str | None = Field(None, alias="Manager")
    approver: str | None = Field(None, alias="Approver")
    reviewer: str | None = Field(None, alias="Reviewer")
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
        return datetime.strptime(v, "%Y%m%d").date()  # noqa: DTZ007

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

    @model_validator(mode="after")
    def check_has_iteration_from_start(self) -> typing.Self:
        iterations_by_date = sorted(self.iterations, key=attrgetter("iteration_date"))
        if first_iteration := next(iter(iterations_by_date), None):
            if first_iteration.iteration_date > self.start_date:
                message = (
                    f"campaign {self.id} starts on {self.start_date}, "
                    f"1st iteration starts later - {first_iteration.iteration_date}"
                )
                raise ValueError(message)
            return self
        # Should never happen, since we are constraining self.iterations with a min_length of 1
        message = f"campaign {self.id} has no iterations."
        raise ValueError(message)

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
