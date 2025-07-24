from collections.abc import Collection, Iterator
from itertools import groupby
from operator import attrgetter

from wireup import service

from eligibility_signposting_api.model import eligibility_status, rules


@service
class CampaignEvaluator:
    """Filters and groups campaign configurations."""

    def get_active_campaigns(self, campaign_configs: Collection[rules.CampaignConfig]) -> list[rules.CampaignConfig]:
        return [cc for cc in campaign_configs if cc.campaign_live]

    def get_requested_grouped_campaigns(
        self, campaign_configs: Collection[rules.CampaignConfig], conditions: list[str], category: str
    ) -> Iterator[tuple[eligibility_status.ConditionName, list[rules.CampaignConfig]]]:
        mapping = {
            "ALL": {"V", "S"},
            "VACCINATIONS": {"V"},
            "SCREENING": {"S"},
        }

        allowed_types = mapping.get(category, set())

        filter_all_conditions = "ALL" in conditions

        active_campaigns = self.get_active_campaigns(campaign_configs)

        for condition_name, campaign_group in groupby(
            sorted(active_campaigns, key=attrgetter("target")),
            key=attrgetter("target"),
        ):
            campaigns = list(campaign_group)
            if (
                campaigns
                and campaigns[0].type in allowed_types
                and (filter_all_conditions or str(condition_name) in conditions)
            ):
                yield condition_name, campaigns
