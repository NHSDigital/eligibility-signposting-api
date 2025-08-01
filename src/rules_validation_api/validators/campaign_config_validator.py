from pydantic import Field

from eligibility_signposting_api.model.campaign_config import CampaignConfig
from rules_validation_api.validators.iteration_validator import IterationValidation


class CampaignConfigValidation(CampaignConfig):
    iterations: list[IterationValidation] = Field(..., min_length=1, alias="Iterations")
