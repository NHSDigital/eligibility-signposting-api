from typing import NewType

from pydantic import BaseModel, RootModel, Field

from eligibility_signposting_api.model.campaign_config import CampaignID

ConsumerId = NewType("ConsumerId", str)


class ConsumerCampaign(BaseModel):
    campaign: CampaignID = Field(alias="Campaign")
    description: str | None = Field(default=None, alias="Description")


class ConsumerMapping(RootModel[dict[ConsumerId, list[ConsumerCampaign]]]):
    def get(self, key: ConsumerId, default: list[ConsumerCampaign] | None = None) -> list[ConsumerCampaign] | None:
        return self.root.get(key, default)
