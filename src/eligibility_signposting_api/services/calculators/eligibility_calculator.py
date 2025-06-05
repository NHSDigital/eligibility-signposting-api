from __future__ import annotations

from _operator import attrgetter
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import groupby
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eligibility_signposting_api.model.rules import Iteration, IterationCohort

from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import (
    CohortResult,
    Condition,
    ConditionName,
    IterationResult,
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

    @property
    def person_cohorts(self) -> set[str]:
        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (row for row in self.person_data if row.get("ATTRIBUTE_TYPE") == "COHORTS"), {}
        )
        return set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

    @staticmethod
    def get_best_cohort(cohort_results: dict[str, CohortResult]) -> tuple[Status, list[CohortResult]]:
        if not cohort_results:
            return eligibility.Status.not_eligible, []
        best_status = eligibility.Status.best(*[result.status for result in cohort_results.values()])
        best_cohorts = [result for result in cohort_results.values() if result.status == best_status]
        return best_status, best_cohorts

    @staticmethod
    def get_exclusion_rules(
        cohort: IterationCohort, rules_filter: Iterable[rules.IterationRule]
    ) -> Iterator[rules.IterationRule]:
        return (
            ir
            for ir in rules_filter
            if ir.cohort_label is None
            or cohort.cohort_label == ir.cohort_label
            or (isinstance(ir.cohort_label, (list, set, tuple)) and cohort.cohort_label in ir.cohort_label)
        )

    @staticmethod
    def get_rules_by_type(
        active_iteration: Iteration,
    ) -> tuple[tuple[rules.IterationRule, ...], tuple[rules.IterationRule, ...]]:
        rules_by_type = {
            rule_type: tuple(rule for rule in active_iteration.iteration_rules if attrgetter("type")(rule) == rule_type)
            for rule_type in (rules.RuleType.filter, rules.RuleType.suppression, rules.RuleType.redirect)
        }
        rules_filter = rules_by_type[rules.RuleType.filter]
        rules_suppression = rules_by_type[rules.RuleType.suppression]
        return rules_filter, rules_suppression

    def evaluate_eligibility(self) -> eligibility.EligibilityStatus:
        """Iterates over campaign groups, evaluates eligibility, and returns a consolidated status."""
        results: dict[ConditionName, IterationResult] = {}

        for condition_name, campaign_group in self.campaigns_grouped_by_condition_name:
            iteration_results: dict[str, IterationResult] = {}

            for active_iteration in [cc.current_iteration for cc in campaign_group]:
                cohort_results: dict[str, CohortResult] = {}

                rules_filter, rules_suppression = self.get_rules_by_type(active_iteration)
                for cohort in sorted(active_iteration.iteration_cohorts, key=attrgetter("priority")):
                    # Check Base Eligibility
                    if cohort.cohort_label in self.person_cohorts or cohort.cohort_label == magic_cohort:
                        is_eligible: bool = True
                        is_eligible = self.evaluate_filter_rules(
                            cohort,
                            cohort_results,
                            rules_filter,
                            is_eligible=is_eligible,
                        )

                        if is_eligible:
                            is_actionable: bool = True
                            suppression_reasons, is_actionable = self.evaluate_suppression_rules(
                                cohort,
                                rules_suppression,
                                is_actionable=is_actionable,
                            )
                            if cohort.cohort_label is not None:
                                key = cohort.cohort_label
                                if is_actionable:
                                    cohort_results[key] = CohortResult(
                                        cohort.cohort_group if cohort.cohort_group else key,
                                        Status.actionable,
                                        [],
                                        str(cohort.positive_description),
                                    )
                                else:
                                    cohort_results[key] = CohortResult(
                                        cohort.cohort_group if cohort.cohort_group else key,
                                        Status.not_actionable,
                                        suppression_reasons,
                                        str(cohort.positive_description),
                                    )

                    # Not base eligible
                    elif cohort.cohort_label is not None:
                        cohort_results[cohort.cohort_label] = CohortResult(
                            cohort.cohort_group if cohort.cohort_group else cohort.cohort_label,
                            Status.not_eligible,
                            [],
                            str(cohort.negative_description),
                        )

                # Determine Result between cohorts - get the best
                status, best_cohorts = self.get_best_cohort(cohort_results)
                iteration_results[active_iteration.name] = IterationResult(status, best_cohorts)

            # Determine results between iterations - get the best
            if iteration_results:
                best_candidate = max(iteration_results.values(), key=lambda r: r.status.value)
            else:
                best_candidate = IterationResult(eligibility.Status.not_eligible, [])
            results[condition_name] = best_candidate

        # Consolidate all the results and return
        final_result = [
            Condition(
                condition_name=condition_name,
                status=active_iteration_result.status,
                cohort_results=active_iteration_result.cohort_results,
            )
            for condition_name, active_iteration_result in results.items()
        ]
        return eligibility.EligibilityStatus(conditions=final_result)

    def evaluate_filter_rules(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortResult],
        rules_filter: Iterable[rules.IterationRule],
        *,
        is_eligible: bool,
    ) -> bool:
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, rules_filter), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_actionable, group_exclusions, rule_stop = self.evaluate_rules_priority_group(rule_group)
            if status.is_exclusion:
                if cohort.cohort_label is not None:
                    cohort_results[str(cohort.cohort_label)] = CohortResult(
                        cohort.cohort_group if cohort.cohort_group else cohort.cohort_label,
                        Status.not_eligible,
                        [],
                        str(cohort.negative_description),
                    )
                is_eligible = False
                break
        return is_eligible

    def evaluate_suppression_rules(
        self,
        cohort: IterationCohort,
        rules_suppression: Iterable[rules.IterationRule],
        *,
        is_actionable: bool,
    ) -> tuple[list, bool]:
        priority_getter = attrgetter("priority")
        suppression_reasons = []
        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, rules_suppression), key=priority_getter)
        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_actionable, group_exclusions, rule_stop = self.evaluate_rules_priority_group(rule_group)
            if status.is_exclusion:
                is_actionable = False
                suppression_reasons.extend(group_exclusions)
                if rule_stop:
                    break
        return suppression_reasons, is_actionable

    def evaluate_rules_priority_group(
        self, rules_group: Iterator[rules.IterationRule]
    ) -> tuple[eligibility.Status, list[eligibility.Reason], list[eligibility.Reason], bool]:
        is_rule_stop = False
        actionable_reasons, exclusion_reasons = [], []
        best_status = eligibility.Status.not_eligible

        for rule in rules_group:
            is_rule_stop = rule.rule_stop or is_rule_stop
            rule_calculator = RuleCalculator(person_data=self.person_data, rule=rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status = eligibility.Status.best(status, best_status)
                exclusion_reasons.append(reason)
            else:
                best_status = eligibility.Status.actionable
                actionable_reasons.append(reason)

        return best_status, actionable_reasons, exclusion_reasons, is_rule_stop
