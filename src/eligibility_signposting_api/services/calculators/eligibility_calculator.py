from __future__ import annotations

from _operator import add, attrgetter
from collections import defaultdict
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass, field
from functools import cached_property, reduce
from itertools import groupby
from typing import Any

from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import (
    CohortStatus,
    Condition,
    ConditionName,
    IterationStatus,
    Status,
)
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator

Row = Collection[Mapping[str, Any]]
magic_cohort = "elid_all_people"


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

    @property
    def active_campaigns(self) -> list[rules.CampaignConfig]:
        return [cc for cc in self.campaign_configs if cc.campaign_live]

    @property
    def campaigns_grouped_by_condition_name(
        self,
    ) -> Iterator[tuple[eligibility.ConditionName, list[rules.CampaignConfig]]]:
        """Generator function to iterate over campaign groups by condition name."""

        for condition_name, campaign_group in groupby(
            sorted(self.active_campaigns, key=attrgetter("target")), key=attrgetter("target")
        ):
            yield condition_name, list(campaign_group)

    @cached_property
    def person_cohorts(self) -> set[str]:
        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (row for row in self.person_data if row.get("ATTRIBUTE_TYPE") == "COHORTS"), {}
        )
        return set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

    def evaluate_eligibility_back_up(self) -> eligibility.EligibilityStatus:
        """Iterates over campaign groups, evaluates eligibility, and returns a consolidated status."""

        for condition_name, campaign_group in self.campaigns_grouped_by_condition_name:
            if base_eligible_campaigns := self.get_the_base_eligible_campaigns(campaign_group):
                status, reasons = self.evaluate_eligibility_by_iteration_rules(base_eligible_campaigns)
                # Append the evaluation result for this condition to the results list
                self.results.append(eligibility.Condition(condition_name, status, reasons))
            else:
                # Create and append the evaluation result, as no campaign config is base eligible
                self.results.append(eligibility.Condition(condition_name, eligibility.Status.not_eligible, []))

        # Return the overall eligibility status, constructed from the list of condition results
        return eligibility.EligibilityStatus(conditions=list(self.results))

    from collections import defaultdict

    # Assuming cohort_results contains tuples of (IterationCohort, Status, list[Reason])
    def get_best_cohort(self, cohort_results: dict[str, CohortStatus]) -> tuple[Status, list[CohortStatus]]:
        # Find the best status across cohorts
        best_status = eligibility.Status.best(*[result.status for result in cohort_results.values()])

        # Filter cohorts that match the best status
        best_cohorts = [result for result in cohort_results.values() if result.status == best_status]
        return best_status, best_cohorts

    def evaluate_eligibility(self) -> eligibility.EligibilityStatus:
        """Iterates over campaign groups, evaluates eligibility, and returns a consolidated status."""
        priority_getter = attrgetter("priority")
        results: dict[ConditionName, IterationStatus] = defaultdict()
        for condition_name, campaign_group in self.campaigns_grouped_by_condition_name:
            iteration_results: dict[str, IterationStatus] = defaultdict()
            for active_iteration in [cc.current_iteration for cc in campaign_group]:
                cohort_results: dict[str, CohortStatus] = defaultdict()

                # Get the rules for this iteration
                rules_filter, rules_suppression, rules_redirect = {
                    rule_type: tuple(
                        rule for rule in active_iteration.iteration_rules if attrgetter("type")(rule) == rule_type
                    )
                    for rule_type in (rules.RuleType.filter, rules.RuleType.suppression, rules.RuleType.redirect)
                }.values()

                for cohort in sorted(active_iteration.iteration_cohorts, key=priority_getter):
                    # Check base Eligibility
                    if cohort.cohort_label in self.person_cohorts:
                        # Base eligible
                        # Check Eligibility - F - Rules
                        eligibility_flag: bool = True
                        for _, rule_group in groupby(sorted(rules_filter, key=priority_getter), key=priority_getter):
                            # iter F rules by priority and grouping
                            # find first exclusion - throws
                            status, group_actionable, group_exclusions = self.evaluate_rules_priority_group(rule_group)
                            if status.is_exclusion:
                                cohort_results[cohort.cohort_label] = CohortStatus(cohort, status, group_exclusions)
                                eligibility_flag = False
                                break

                        if eligibility_flag:
                            actionable_flag: bool = True
                            for _, rule_group in groupby(
                                sorted(rules_suppression, key=priority_getter), key=priority_getter
                            ):
                                # iter S rules by priority and grouping
                                # find first exclusion - throws
                                status, group_actionable, group_exclusions = self.evaluate_rules_priority_group(
                                    rule_group
                                )
                                if status.is_exclusion:
                                    cohort_results[cohort.cohort_label] = CohortStatus(cohort, status, group_exclusions)
                                    actionable_flag = False
                                    break
                            # No exclusions - actionable
                            if actionable_flag:
                                cohort_results[cohort.cohort_label] = CohortStatus(cohort, Status.actionable, [])
                    else:
                        # Not base eligibility
                        cohort_results[cohort.cohort_label] = CohortStatus(cohort, eligibility.Status.not_eligible, [])

                # Determine Result between cohorts - get the best
                iteration_results[active_iteration.name] = IterationStatus(
                    *self.get_best_cohort(cohort_results)
                )  # multiple
            # Determine results between iterations - get the best
            best_candidate = max(iteration_results.values(), key=lambda r: r.status.value)
            results[condition_name] = best_candidate

        # Consolidate all the results and return
        final_result = [
            Condition(
                condition_name=condition_name,
                status=iteration_result.status,
                reasons=reduce(add, [cohort.reasons for cohort in iteration_result.cohort_status], []),
            )
            for condition_name, iteration_result in results.items()
        ]
        return eligibility.EligibilityStatus(conditions=final_result)

    def get_the_base_eligible_campaigns(self, campaign_group: list[rules.CampaignConfig]) -> list[rules.CampaignConfig]:
        """Return campaigns for which the person is base eligible via cohorts."""

        base_eligible_campaigns: list[rules.CampaignConfig] = [
            campaign for campaign in campaign_group if self.check_base_eligibility(campaign.current_iteration)
        ]

        if base_eligible_campaigns:
            return base_eligible_campaigns
        return []

    def check_base_eligibility(self, iteration: rules.Iteration) -> bool:
        """Return cohorts for which person is base eligible."""
        iteration_cohorts: set[str] = {
            cohort.cohort_label for cohort in iteration.iteration_cohorts if cohort.cohort_label
        }
        if magic_cohort in iteration_cohorts:
            return True
        return bool(iteration_cohorts & self.person_cohorts)

    def evaluate_eligibility_by_iteration_rules(
        self, campaign_group: list[rules.CampaignConfig]
    ) -> tuple[eligibility.Status, list[eligibility.Reason]]:
        """Evaluate iteration rules to see if the person is actionable, not actionable (due to "S" rules),
        or not eligible (due to "F" rules").

        For each condition, evaluate all iterations for inclusion or exclusion."""

        priority_getter = attrgetter("priority")

        status_with_reasons: dict[eligibility.Status, list[eligibility.Reason]] = defaultdict()

        for iteration in [cc.current_iteration for cc in campaign_group]:
            # Until we see a worse status, we assume someone is actionable for this iteration.
            worst_status = eligibility.Status.actionable
            exclusion_reasons, actionable_reasons = [], []
            by_priority = sorted(iteration.iteration_rules, key=priority_getter)
            for _, rule_group in groupby(by_priority, key=priority_getter):
                status, group_actionable, group_exclusions, is_rule_stop = self.evaluate_priority_group(
                    rule_group, worst_status
                )
                # Merge results
                worst_status = status
                actionable_reasons.extend(group_actionable)
                exclusion_reasons.extend(group_exclusions)
                if is_rule_stop:
                    break
            condition_status_entry = status_with_reasons.setdefault(worst_status, [])
            condition_status_entry.extend(
                actionable_reasons if worst_status is eligibility.Status.actionable else exclusion_reasons
            )

        best_status = eligibility.Status.best(*list(status_with_reasons.keys()))

        return best_status, status_with_reasons[best_status]

    def evaluate_priority_group(
        self,
        iteration_rule_group: Iterator[rules.IterationRule],
        worst_status_so_far_for_condition: eligibility.Status,
    ) -> tuple[eligibility.Status, list[eligibility.Reason], list[eligibility.Reason], bool]:
        is_rule_stop = False
        exclusion_reasons, actionable_reasons = [], []
        exclude_capable_rules = [
            ir
            for ir in iteration_rule_group
            if ir.type in (rules.RuleType.filter, rules.RuleType.suppression)
            and (ir.cohort_label is None or (ir.cohort_label in self.person_cohorts))
        ]

        best_status = eligibility.Status.not_eligible if exclude_capable_rules else eligibility.Status.actionable

        for rule in exclude_capable_rules:
            rule_calculator = RuleCalculator(person_data=self.person_data, rule=rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status = eligibility.Status.best(status, best_status)
                exclusion_reasons.append(reason)
            else:
                best_status = eligibility.Status.actionable
                actionable_reasons.append(reason)

        worst_group_status = eligibility.Status.worst(best_status, worst_status_so_far_for_condition)
        if worst_group_status.is_exclusion:
            is_rule_stop = any(rule.rule_stop for rule in exclude_capable_rules)
        return worst_group_status, actionable_reasons, exclusion_reasons, is_rule_stop

    def evaluate_rules_priority_group(
        self, iteration_rule_group: Iterator[rules.IterationRule]
    ) -> tuple[eligibility.Status, list[eligibility.Reason], list[eligibility.Reason]]:
        exclusion_reasons, actionable_reasons = [], []
        exclude_capable_rules = [
            ir
            for ir in iteration_rule_group
            if ir.type in (rules.RuleType.filter, rules.RuleType.suppression)
            and (ir.cohort_label is None or (ir.cohort_label in self.person_cohorts))
        ]
        best_status = eligibility.Status.not_eligible if exclude_capable_rules else eligibility.Status.actionable

        for rule in exclude_capable_rules:
            rule_calculator = RuleCalculator(person_data=self.person_data, rule=rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status = eligibility.Status.best(status, best_status)
                exclusion_reasons.append(reason)
            else:
                best_status = eligibility.Status.actionable
                actionable_reasons.append(reason)

        return best_status, actionable_reasons, exclusion_reasons
