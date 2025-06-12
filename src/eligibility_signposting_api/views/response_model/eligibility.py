from datetime import datetime
from enum import StrEnum
from typing import NewType, Optional, List

from pydantic import UUID4, BaseModel, Field, HttpUrl, field_serializer
from pydantic_core.core_schema import SerializationInfo

LastUpdated = NewType("LastUpdated", datetime)
ConditionName = NewType("ConditionName", str)
StatusText = NewType("StatusText", str)
ActionType = NewType("ActionType", str)
ActionCode = NewType("ActionCode", str)
Description = NewType("Description", str)
RuleCode = NewType("RuleCode", str)
RuleText = NewType("RuleText", str)
CohortCode = NewType("CohortCode", str)
CohortText = NewType("CohortText", str)


class Status(StrEnum):
    not_eligible = "NotEligible"
    not_actionable = "NotActionable"
    actionable = "Actionable"


class RuleType(StrEnum):
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
    actions: Optional[list[Action]]

    model_config = {"populate_by_name": True}


class Meta(BaseModel):
    last_updated: LastUpdated = Field(..., alias="lastUpdated")

    model_config = {"populate_by_name": True}

    @field_serializer("last_updated")
    def serialize_last_updated(self, last_updated: LastUpdated, _info: SerializationInfo) -> str:
        return last_updated.isoformat()


class EligibilityResponse(BaseModel):
    """Pydantic model for creating our API response as specified in
    https://github.com/NHSDigital/eligibility-signposting-api-specification/blob/main/specification/eligibility-signposting-api.yaml"""

    response_id: UUID4 = Field(..., alias="responseId")
    meta: Meta
    processed_suggestions: list[ProcessedSuggestion] = Field(..., alias="processedSuggestions")

    model_config = {"populate_by_name": True}
