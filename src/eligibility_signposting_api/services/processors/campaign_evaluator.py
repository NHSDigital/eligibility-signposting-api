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

    def get_campaign_with_latest_iteration(self, active_campaigns: list[CampaignConfig]) -> CampaignConfig:

        """
            Returns the campaign with the latest active iteration date.

            1. Collect all campaigns with an active iteration.
            2. Sort by iteration date (descending).
            3. Extract the lead campaign, throwing an error if a tie for the latest date exists.
        """

        if not active_campaigns:
            return None

        valid_items = [
            (cc.current_iteration.iteration_date, cc)
            for cc in active_campaigns if cc.current_iteration
        ]

        if not valid_items:
            latest_date, latest_campaign = None, None
        else:
            max_date = max(item[0] for item in valid_items)
            cc_with_max_iteration_date = [item for item in valid_items if item[0] == max_date]
            if len(cc_with_max_iteration_date) > 1:
                raise ValueError(f"Ambiguous result: {len(cc_with_max_iteration_date)} campaigns found for date {max_date}")

            latest_date, latest_campaign = cc_with_max_iteration_date[0]

        return latest_campaign

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
            filtered_campaigns = [c for c in allowed_campaigns if filter_all_conditions or str(condition_name) in conditions]

            yield condition_name, self.get_campaign_with_latest_iteration(filtered_campaigns)
