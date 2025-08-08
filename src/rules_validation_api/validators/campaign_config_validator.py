from pydantic import field_validator

from eligibility_signposting_api.model.campaign_config import CampaignConfig, Iteration
from rules_validation_api.validators.iteration_validator import IterationValidation


class CampaignConfigValidation(CampaignConfig):
    @field_validator("iterations")
    @classmethod
    def validate_iterations(cls, iterations: list[Iteration]) -> list[IterationValidation]:
        return [IterationValidation(**i.model_dump()) for i in iterations]
