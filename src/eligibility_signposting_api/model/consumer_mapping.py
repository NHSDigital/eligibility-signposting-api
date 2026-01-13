from typing import NewType

from pydantic import BaseModel, RootModel

from eligibility_signposting_api.model.campaign_config import CampaignID

ConsumerId = NewType("ConsumerId", str)


class ConsumerCampaign(BaseModel):
    campaign: CampaignID
    description: str | None = None


class ConsumerMapping(RootModel[dict[ConsumerId, list[ConsumerCampaign]]]):
    def get(self, key: ConsumerId, default: list[ConsumerCampaign] | None = None) -> list[ConsumerCampaign] | None:
        return self.root.get(key, default)
