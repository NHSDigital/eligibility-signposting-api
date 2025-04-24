from enum import Enum
from typing import NewType

from pydantic import BaseModel, Field, HttpUrl

ConditionName = NewType("ConditionName", str)
StatusText = NewType("StatusText", str)
ActionType = NewType("ActionType", str)
ActionCode = NewType("ActionCode", str)
Description = NewType("Description", str)
RuleCode = NewType("RuleCode", str)
RuleText = NewType("RuleText", str)
CohortCode = NewType("CohortCode", str)
CohortText = NewType("CohortText", str)


class Status(str, Enum):
    not_eligible = "NotEligible"
    not_actionable = "NotActionable"
    actionable = "Actionable"


class RuleType(str, Enum):
    filter = "F"
    suppression = "S"
    redirect = "R"


class EligibilityCohort(BaseModel):
    cohort_code: CohortCode = Field(..., alias="cohortCode")
    cohort_text: CohortText = Field(..., alias="cohortText")
    cohort_status: Status = Field(..., alias="cohortStatus")

    model_config = {"populate_by_name": True}


class SuitabilityRule(BaseModel):
    type: RuleType = Field(..., alias="ruleType")
    rule_code: RuleCode = Field(..., alias="ruleCode")
    rule_text: RuleText = Field(..., alias="ruleText")

    model_config = {"populate_by_name": True}


class Action(BaseModel):
    action_type: ActionType = Field(..., alias="actionType")
    action_code: ActionCode = Field(..., alias="actionCode")
    description: Description
    url_link: HttpUrl = Field(..., alias="urlLink")

    model_config = {"populate_by_name": True}


class ProcessedSuggestion(BaseModel):
    condition_name: ConditionName = Field(..., alias="condition")
    status: Status
    status_text: StatusText = Field(..., alias="statusText")
    eligibility_cohorts: list[EligibilityCohort] = Field(..., alias="eligibilityCohorts")
    suitability_rules: list[SuitabilityRule] = Field(..., alias="suitabilityRules")
    actions: list[Action]

    model_config = {"populate_by_name": True}


class EligibilityResponse(BaseModel):
    processed_suggestions: list[ProcessedSuggestion] = Field(..., alias="processedSuggestions")

    model_config = {"populate_by_name": True}
