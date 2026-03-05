import logging
from collections.abc import Collection, Iterator
from itertools import groupby
from operator import attrgetter

from wireup import service

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import CampaignConfig

logger = logging.getLogger(__name__)


@service
class CampaignEvaluator:
    """Filters and groups campaign configurations."""

    def get_active_campaigns(self, campaign_configs: Collection[CampaignConfig]) -> list[CampaignConfig]:
        return [cc for cc in campaign_configs if cc.campaign_live]

    def get_campaign_with_latest_iteration(self, active_campaigns: list[CampaignConfig]) -> CampaignConfig | None:
        """
        Returns the campaign with the latest active iteration date.

        1. Collect all campaigns with an active iteration.
        2. Sort by iteration date (descending).
        3. Extract the lead campaign, throwing an error if a tie for the latest date exists.
        """

        valid_items = []

        for cc in active_campaigns:
            try:
                valid_items.append((cc.current_iteration.iteration_date, cc))
            except StopIteration:
                logger.info(
                    "Skipping campaign ID %s as no active iteration was found.",
                    cc.id,
                )

        if not valid_items:
            latest_campaign = None
        else:
            max_date = max(item[0] for item in valid_items)
            cc_with_max_iteration_date: list[CampaignConfig] = [item[1] for item in valid_items if item[0] == max_date]
            if len(cc_with_max_iteration_date) > 1:
                err_msg = (
                    f"Ambiguous result: '{len(cc_with_max_iteration_date)}' active iterations "
                    f"for target {cc_with_max_iteration_date[0].target} "
                    f"found for date '{max_date}' "
                    f"across campaign(s) {[cc.id for cc in cc_with_max_iteration_date]}"
                )
                raise ValueError(err_msg)

            latest_campaign = cc_with_max_iteration_date[0]

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
            filtered_campaigns = [
                c for c in campaign_group if filter_all_conditions or str(condition_name) in conditions
            ]

            campaign = self.get_campaign_with_latest_iteration(filtered_campaigns)
            if campaign is not None:
                yield (condition_name, campaign)
