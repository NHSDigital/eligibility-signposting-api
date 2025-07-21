from collections.abc import Collection, Iterator
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter

from eligibility_signposting_api.model import eligibility, rules


@dataclass
class CampaignProcessor:
    campaign_configs: Collection[rules.CampaignConfig]

    @property
    def active_campaigns(self) -> list[rules.CampaignConfig]:
        return [cc for cc in self.campaign_configs if cc.campaign_live]

    def get_campaigns_grouped_by_condition_name(
        self, conditions: list[str], category: str
    ) -> Iterator[tuple[eligibility.ConditionName, list[rules.CampaignConfig]]]:
        mapping = {
            "ALL": {"V", "S"},
            "VACCINATIONS": {"V"},
            "SCREENING": {"S"},
        }

        allowed_types = mapping.get(category, set())

        filter_all_conditions = "ALL" in conditions

        for condition_name, campaign_group in groupby(
            sorted(self.active_campaigns, key=attrgetter("target")),
            key=attrgetter("target"),
        ):
            campaigns = list(campaign_group)
            if campaigns[0].type in allowed_types and (filter_all_conditions or str(condition_name) in conditions):
                yield condition_name, campaigns
