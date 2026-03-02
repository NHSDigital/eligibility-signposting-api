from collections.abc import Collection, Iterator
from itertools import groupby
from operator import attrgetter

from wireup import service

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import CampaignConfig


@service
class CampaignEvaluator:
    """Filters and groups campaign configurations."""

    def get_active_campaigns(self, campaign_configs: Collection[CampaignConfig]) -> list[CampaignConfig]:
        return [cc for cc in campaign_configs if cc.campaign_live]

    def get_latest_campaign(self, campaign_group: list[CampaignConfig]):
        if not campaign_group:
            return None

        latest_date = max(c.start_date for c in campaign_group)

        latest = [c for c in campaign_group if c.start_date == latest_date]

        if len(latest) == 1:
            return latest[0]

        if len(latest) > 1:
            raise ValueError(
                f"Multiple campaigns share the latest start_date: {latest_date}")  # TODO handle it in FHIR format

        return None

    def get_campaign_with_latest_active_iteration_per_target(
        self, campaign_configs: Collection[CampaignConfig], conditions: list[str], requested_category: str
    ) -> Iterator[tuple[eligibility_status.ConditionName, CampaignConfig]]:
        mapping = {
            "ALL": {"V", "S"},
            "VACCINATIONS": {"V"},
            "SCREENING": {"S"},
        }

        allowed_types = mapping.get(requested_category, set())

        filter_all_conditions = "ALL" in conditions

        allowed_campaigns = [c for c in campaign_configs if c.type in allowed_types]
        active_campaigns = self.get_active_campaigns(allowed_campaigns)

        for condition_name, campaign_group in groupby(
            sorted(active_campaigns, key=attrgetter("target")),
            key=attrgetter("target"),
        ):
            campaigns = [c for c in allowed_campaigns if filter_all_conditions or str(condition_name) in conditions]

            yield condition_name, self.get_latest_campaign(campaigns)
