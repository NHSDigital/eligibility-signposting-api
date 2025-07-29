from typing import List

from pydantic import field_validator, BaseModel, Field

from eligibility_signposting_api.model.campaign_config import Iteration
from rules_validation_api.validators.iteration_rules_validator import IterationRuleValidation


class IterationValidation(Iteration):
    iteration_rules: List[IterationRuleValidation] = Field(..., min_length=1, alias="IterationRules")

    @field_validator("id")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ID must not be empty")
        return value

    @field_validator("id")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ID must not be empty")
        return value


