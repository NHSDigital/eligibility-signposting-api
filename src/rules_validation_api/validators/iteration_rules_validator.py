from pydantic import field_validator

from eligibility_signposting_api.model.campaign_config import ActionsMapper, IterationRule


class IterationRuleValidation(IterationRule):
    @field_validator("type")
    def validate_type(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("type must not be empty")
        return value
