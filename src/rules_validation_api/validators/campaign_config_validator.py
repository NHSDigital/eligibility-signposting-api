from pydantic import Field, field_validator

from eligibility_signposting_api.model.campaign_config import CampaignConfig, Iteration
from rules_validation_api.validators.iteration_validator import IterationValidation


class CampaignConfigValidation(CampaignConfig):
    iterations: list[Iteration] = Field(..., min_length=1, alias="Iterations")

    @classmethod
    @field_validator("iterations")
    def validate_iterations(cls, iterations: list[Iteration]) -> list[IterationValidation]:
        return [IterationValidation(**i.model_dump()) for i in iterations]
