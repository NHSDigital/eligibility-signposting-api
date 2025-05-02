from __future__ import annotations

import typing
from datetime import date, datetime
from enum import Enum
from typing import Literal, NewType

from pydantic import BaseModel, Field, field_serializer, field_validator

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
RuleComparator = NewType("RuleComparator", str)
StartDate = NewType("StartDate", date)
EndDate = NewType("EndDate", date)


class RuleType(str, Enum):
    filter = "F"
    suppression = "S"
    redirect = "R"


class RuleOperator(str, Enum):
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


class RuleAttributeLevel(str, Enum):
    PERSON = "PERSON"
    TARGET = "TARGET"
    COHORT = "COHORT"


class IterationCohort(BaseModel):
    cohort_label: str | None = Field(None, alias="CohortLabel")
    priority: int | None = Field(None, alias="Priority")

    model_config = {"populate_by_name": True}


class IterationRule(BaseModel):
    type: RuleType = Field(..., alias="Type")
    name: RuleName = Field(..., alias="Name")
    description: RuleDescription = Field(..., alias="Description")
    priority: RulePriority = Field(..., alias="Priority")
    attribute_level: RuleAttributeLevel = Field(..., alias="AttributeLevel")
    attribute_name: RuleAttributeName = Field(..., alias="AttributeName")
    operator: RuleOperator = Field(..., alias="Operator")
    comparator: RuleComparator = Field(..., alias="Comparator")
    attribute_target: str | None = Field(None, alias="AttributeTarget")

    model_config = {"populate_by_name": True}


class Iteration(BaseModel):
    id: IterationID = Field(..., alias="ID")
    version: IterationVersion = Field(..., alias="Version")
    name: IterationName = Field(..., alias="Name")
    iteration_date: IterationDate = Field(..., alias="IterationDate")
    iteration_number: int | None = Field(None, alias="IterationNumber")
    approval_minimum: int | None = Field(None, alias="ApprovalMinimum")
    approval_maximum: int | None = Field(None, alias="ApprovalMaximum")
    type: Literal["A", "M", "S"] = Field(..., alias="Type")
    iteration_cohorts: list[IterationCohort] = Field(..., alias="IterationCohorts")
    iteration_rules: list[IterationRule] = Field(..., alias="IterationRules")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

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
    iteration_type: Literal["A", "M", "S"] = Field(..., alias="IterationType")
    iteration_time: str | None = Field(None, alias="IterationTime")
    default_comms_routing: str | None = Field(None, alias="DefaultCommsRouting")
    start_date: StartDate = Field(..., alias="StartDate")
    end_date: EndDate = Field(..., alias="EndDate")
    approval_minimum: int | None = Field(None, alias="ApprovalMinimum")
    approval_maximum: int | None = Field(None, alias="ApprovalMaximum")
    iterations: list[Iteration] = Field(..., alias="Iterations")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

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


class Rules(BaseModel):
    """Eligibility rules.

    This is a Pydantic model, into which we can de-serialise rules stored in DPS's format."""

    campaign_config: CampaignConfig = Field(..., alias="CampaignConfig")

    model_config = {"populate_by_name": True}
