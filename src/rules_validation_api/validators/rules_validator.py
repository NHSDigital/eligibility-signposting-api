from pydantic import field_validator

from eligibility_signposting_api.model.campaign_config import CampaignConfig, Rules
from rules_validation_api.validators.campaign_config_validator import CampaignConfigValidation


class RulesValidation(Rules):
    @classmethod
    @field_validator("campaign_config")
    def validate_campaign_config(cls, campaign_config: CampaignConfig) -> CampaignConfig:
        return CampaignConfigValidation(**campaign_config.model_dump())
