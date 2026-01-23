from typing import NewType

from pydantic import BaseModel, Field, RootModel

from eligibility_signposting_api.model.campaign_config import CampaignID

ConsumerId = NewType("ConsumerId", str)


class ConsumerCampaign(BaseModel):
    campaign_config_id: CampaignID = Field(alias="CampaignConfigId")
    description: str | None = Field(default=None, alias="Description")


class ConsumerMapping(RootModel[dict[ConsumerId, list[ConsumerCampaign]]]):
    def get(self, key: ConsumerId, default: list[ConsumerCampaign] | None = None) -> list[ConsumerCampaign] | None:
        return self.root.get(key, default)
