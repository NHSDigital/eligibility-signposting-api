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
                    # Check Base Eligibility
                    if cohort.cohort_label in self.person_cohorts or cohort.cohort_label == magic_cohort:
                        # Base eligible
                        # Check Eligibility - F - Rules
                        eligibility_flag: bool = True
                        exclusion_capable_filter_rules = (
                            ir
                            for ir in rules_filter
                            if ir.cohort_label is None or ir.cohort_label in cohort.cohort_label
                        )
                        for _, rule_group in groupby(
                            sorted(exclusion_capable_filter_rules, key=priority_getter), key=priority_getter
                        ):
                            # iter F rules by priority and grouping
                            # find first exclusion - throws
                            status, group_actionable, group_exclusions, rule_stop = self.evaluate_rules_priority_group(
                                rule_group
                            )
                            if status.is_exclusion:
                                cohort_results[cohort.cohort_label] = CohortStatus(cohort, status, group_exclusions)
                                eligibility_flag = False
                                break
                        # Eligible
                        # Check Actionable(ity) - S - Rules
                        if eligibility_flag:
                            actionable_flag: bool = True
                            suppression_reasons = []
                            exclusion_capable_suppression_rules = (
                                ir
                                for ir in rules_suppression
                                if ir.cohort_label is None or ir.cohort_label in cohort.cohort_label
                            )
                            for _, rule_group in groupby(
                                sorted(exclusion_capable_suppression_rules, key=priority_getter), key=priority_getter
                            ):
                                # iter S rules by priority and grouping
                                # find first exclusion - throws
                                status, group_actionable, group_exclusions, rule_stop = (
                                    self.evaluate_rules_priority_group(rule_group)
                                )
                                if status.is_exclusion:
                                    actionable_flag = False
                                    suppression_reasons.extend(group_exclusions)
                                    if rule_stop:
                                        break
                            # No exclusions - actionable
                            if actionable_flag:
                                cohort_results[cohort.cohort_label] = CohortStatus(cohort, Status.actionable, [])
                            else:
                                cohort_results[cohort.cohort_label] = CohortStatus(
                                    cohort, Status.not_actionable, suppression_reasons
                                )

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
                status=active_iteration_result.status,
                cohort_results=active_iteration_result.cohort_statuses,
            )
            for condition_name, active_iteration_result in results.items()
        ]
        return eligibility.EligibilityStatus(conditions=final_result)

    def evaluate_rules_priority_group(
        self, iteration_rule_group: Iterator[rules.IterationRule]
    ) -> tuple[eligibility.Status, list[eligibility.Reason], list[eligibility.Reason], bool]:
        is_rule_stop: bool = False

        exclusion_reasons, actionable_reasons = [], []

        best_status = eligibility.Status.not_eligible

        for rule in iteration_rule_group:
            is_rule_stop = True if rule.rule_stop else is_rule_stop
            rule_calculator = RuleCalculator(person_data=self.person_data, rule=rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status = eligibility.Status.best(status, best_status)
                exclusion_reasons.append(reason)
            else:
                best_status = eligibility.Status.actionable
                actionable_reasons.append(reason)

        return best_status, actionable_reasons, exclusion_reasons, is_rule_stop
