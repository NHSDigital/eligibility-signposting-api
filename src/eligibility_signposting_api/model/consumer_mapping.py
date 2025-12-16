from typing import NewType

from pydantic import RootModel

from eligibility_signposting_api.model.campaign_config import CampaignID

ConsumerId = NewType("ConsumerId", str)

class ConsumerMapping(RootModel[dict[str, list[CampaignID]]]):
    def get(self, key: str, default: list[CampaignID] | None = None) -> list[CampaignID] | None:
        return self.root.get(key, default)
