from pydantic import Field, field_validator

from eligibility_signposting_api.model.campaign_config import CampaignConfig
from rules_validation_api.validators.iteration_validator import IterationValidation


class CampaignConfigValidation(CampaignConfig):
    iterations: list[IterationValidation] = Field(..., min_length=1, alias="Iterations")

    @field_validator("id")
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("campaign ID must not be empty")
        return value

    @field_validator("type")
    def validate_type(cls, value: str) -> str:
        allowed_values = {"V", "S"}
        if value not in allowed_values:
            raise ValueError(f"type must be one of {allowed_values}")
        return value
