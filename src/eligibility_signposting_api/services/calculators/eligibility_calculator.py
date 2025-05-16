from __future__ import annotations

from _operator import attrgetter
from collections import defaultdict
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from itertools import groupby
from typing import Any

from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import Reason, Status
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator

Row = Collection[Mapping[str, Any]]


@service
class EligibilityCalculatorFactory:
    @staticmethod
    def get(person_data: Row, campaign_configs: Collection[rules.CampaignConfig]) -> EligibilityCalculator:
        return EligibilityCalculator(person_data=person_data, campaign_configs=campaign_configs)


@dataclass
class EligibilityCalculator:
    person_data: Row
    campaign_configs: Collection[rules.CampaignConfig]

    results: list[eligibility.Condition] = field(default_factory=list)

    @cached_property
    def condition_names(self) -> set[eligibility.ConditionName]:
        return {
            eligibility.ConditionName(cc.target)
            for cc in self.campaign_configs
            if cc.campaign_live and cc.current_iteration
        }

    def evaluate_eligibility(self) -> eligibility.EligibilityStatus:
        # Group campaign configs by their 'target' attribute and sort each group by 'target'
        campaign_configs_grouped_by_condition_name = {
            key: sorted(campaign_group, key=attrgetter("target"))
            for key, campaign_group in groupby(self.campaign_configs, key=attrgetter("target"))
        }

        # Iterate over each group of campaign configs
        for condition_name, campaign_group in campaign_configs_grouped_by_condition_name.items():
            # Skip processing if the condition name is not in the set of valid condition names
            if condition_name not in self.condition_names:
                continue

            # Get the base eligible campaigns or base ineligibility reasons for the current group
            base_eligible_campaigns, status, reasons = (
                self.get_the_base_eligible_campaigns_or_base_ineligibility_reasons(campaign_group)
            )

            # If there are base eligible campaigns, further evaluate them by iteration rules
            if base_eligible_campaigns:
                status, reasons = self.evaluate_eligibility_by_iteration_rules(base_eligible_campaigns)

            # Append the evaluation result for this condition to the results list
            self.results.append(eligibility.Condition(condition_name, status, reasons))

        # Return the overall eligibility status, constructed from the list of condition results
        return eligibility.EligibilityStatus(conditions=list(self.results))

    def get_the_base_eligible_campaigns_or_base_ineligibility_reasons(
        self, campaign_group: list[rules.CampaignConfig]
    ) -> tuple[list[rules.CampaignConfig], Status, list[Reason]]:
        """Get all campaigns in the group for which the person is base eligible,
                                                                        i.e. those which *might* provide eligibility.

        Build and return a collection of campaigns for which the person is base eligible (using cohorts),
        Otherwise, build and return the in-eligibility status and reasons
        """
        base_eligible_campaigns: list[rules.CampaignConfig] = []

        for campaign_config in (cc for cc in campaign_group if cc.campaign_live and cc.current_iteration):
            base_eligible = self.check_base_eligibility(campaign_config.current_iteration)
            if base_eligible:
                base_eligible_campaigns.append(campaign_config)

        if base_eligible_campaigns:
            return base_eligible_campaigns, Status.nothing, []
        return [], eligibility.Status.not_eligible, []

    def check_base_eligibility(self, iteration: rules.Iteration | None) -> set[str]:
        """Return cohorts for which person is base eligible."""
        if not iteration or not iteration.iteration_cohorts:
            return set()
        # Extract iteration cohorts efficiently
        iteration_cohorts: set[str] = {
            cohort.cohort_label for cohort in iteration.iteration_cohorts if cohort.cohort_label
        }
        # Locate person's cohorts safely
        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (r for r in self.person_data if r.get("ATTRIBUTE_TYPE") == "COHORTS"), {}
        )
        person_cohorts = set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

        return iteration_cohorts & person_cohorts

    def evaluate_eligibility_by_iteration_rules(
        self, campaign_group: list[rules.CampaignConfig]
    ) -> tuple[Status, list[Reason]]:
        """Evaluate iteration rules to see if the person is actionable, not actionable (due to "F" rules),
        or not eligible (due to "S" rules").

        For each condition, evaluate all iterations for inclusion or exclusion."""

        priority_getter = attrgetter("priority")

        status_reason_dict: dict[Status, list[Reason]] = defaultdict()

        for iteration in [cc.current_iteration for cc in campaign_group if cc.current_iteration]:
            # Until we see a worse status, we assume someone is actionable for this iteration.
            worst_status_so_far_for_condition = eligibility.Status.actionable
            exclusion_reasons, actionable_reasons = [], []
            for _priority, iteration_rule_group in groupby(
                sorted(iteration.iteration_rules, key=priority_getter), key=priority_getter
            ):
                (
                    worst_status_so_far_for_condition,
                    campaign_group_actionable_reasons,
                    campaign_group_exclusion_reasons,
                ) = self.evaluate_priority_group(iteration_rule_group, worst_status_so_far_for_condition)
                actionable_reasons.extend(campaign_group_actionable_reasons)
                exclusion_reasons.extend(campaign_group_exclusion_reasons)
            condition_status_entry = status_reason_dict.setdefault(worst_status_so_far_for_condition, [])
            condition_status_entry.extend(
                actionable_reasons
                if worst_status_so_far_for_condition is eligibility.Status.actionable
                else exclusion_reasons
            )

        best_status = eligibility.Status.best(*list(status_reason_dict.keys()))

        return best_status, status_reason_dict[best_status]

    def evaluate_priority_group(
        self,
        iteration_rule_group: Iterator[rules.IterationRule],
        worst_status_so_far_for_condition: eligibility.Status,
    ) -> tuple[eligibility.Status, list[eligibility.Reason], list[eligibility.Reason]]:
        actionable_reasons, exclusion_reasons = [], []
        exclude_capable_rules = [
            ir for ir in iteration_rule_group if ir.type in (rules.RuleType.filter, rules.RuleType.suppression)
        ]
        best_status_so_far_for_priority_group = (
            eligibility.Status.not_eligible if exclude_capable_rules else eligibility.Status.actionable
        )
        for iteration_rule in exclude_capable_rules:
            rule_calculator = RuleCalculator(person_data=self.person_data, rule=iteration_rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status_so_far_for_priority_group = eligibility.Status.best(
                    status, best_status_so_far_for_priority_group
                )
                exclusion_reasons.append(reason)
            else:
                best_status_so_far_for_priority_group = eligibility.Status.actionable
                actionable_reasons.append(reason)
        return (
            eligibility.Status.worst(best_status_so_far_for_priority_group, worst_status_so_far_for_condition),
            actionable_reasons,
            exclusion_reasons,
        )
