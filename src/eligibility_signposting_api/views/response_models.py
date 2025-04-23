from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class Status(str, Enum):
    not_eligible = "NotEligible"
    not_actionable = "NotActionable"
    actionable = "Actionable"


class RuleType(str, Enum):
    filter = "F"
    suppression = "S"
    redirect = "R"


class EligibilityCohort(BaseModel):
    cohort_code: str = Field(..., alias="cohortCode")
    cohort_text: str = Field(..., alias="cohortText")
    cohort_status: Status = Field(..., alias="cohortStatus")

    model_config = {"populate_by_name": True}


class SuitabilityRule(BaseModel):
    type: RuleType = Field(..., alias="ruleType")
    rule_code: str = Field(..., alias="ruleCode")
    rule_text: str = Field(..., alias="ruleText")

    model_config = {"populate_by_name": True}


class Action(BaseModel):
    action_type: str = Field(..., alias="actionType")
    action_code: str = Field(..., alias="actionCode")
    description: str
    url_link: HttpUrl = Field(..., alias="urlLink")

    model_config = {"populate_by_name": True}


class ProcessedSuggestion(BaseModel):
    condition: str
    status: Status
    status_text: str = Field(..., alias="statusText")
    eligibility_cohorts: list[EligibilityCohort] = Field(..., alias="eligibilityCohorts")
    suitability_rules: list[SuitabilityRule] = Field(..., alias="suitabilityRules")
    actions: list[Action]

    model_config = {"populate_by_name": True}


class EligibilityResponse(BaseModel):
    processed_suggestions: list[ProcessedSuggestion] = Field(..., alias="processedSuggestions")

    model_config = {"populate_by_name": True}
