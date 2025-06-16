from __future__ import annotations

from _operator import attrgetter
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import groupby
from multiprocessing.connection import default_family
from typing import TYPE_CHECKING, Any

#from localstack.utils.testutil import list_all_resources
#from pygments.lexer import default

if TYPE_CHECKING:
    from eligibility_signposting_api.model.rules import Iteration, IterationCohort

from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import (
    CohortResult,
    Condition,
    ConditionName,
    IterationResult,
    Status, Action,
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
        cohort: IterationCohort, filter_rules: Iterable[rules.IterationRule]
    ) -> Iterator[rules.IterationRule]:
        return (
            ir
            for ir in filter_rules
            if ir.cohort_label is None
               or cohort.cohort_label == ir.cohort_label
               or (isinstance(ir.cohort_label, (list, set, tuple)) and cohort.cohort_label in ir.cohort_label)
        )

    @staticmethod
    def get_rules_by_type(
        active_iteration: Iteration,
    ) -> tuple[tuple[rules.IterationRule, ...], tuple[rules.IterationRule, ...]]:
        filter_rules, suppression_rules = (
            tuple(rule for rule in active_iteration.iteration_rules if attrgetter("type")(rule) == rule_type)
            for rule_type in (rules.RuleType.filter, rules.RuleType.suppression)
        )
        return filter_rules, suppression_rules

    @staticmethod
    def get_redirect_rules(
        active_iteration: Iteration,
    ) -> tuple[tuple[rules.IterationRule, ...], dict[str, dict[str, str]], str]:
        redirect_rules = tuple(
            rule for rule in active_iteration.iteration_rules if rule.type in rules.RuleType.redirect
        )
        default_comms = active_iteration.default_comms_routing
        action_mapper = active_iteration.actions_mapper
        return redirect_rules, action_mapper, default_comms

    def evaluate_eligibility(self) -> eligibility.EligibilityStatus:
        """Iterates over campaign groups, evaluates eligibility, and returns a consolidated status."""
        condition_results: dict[ConditionName, IterationResult] = {}
        actions: [Action] = []

        for condition_name, campaign_group in self.campaigns_grouped_by_condition_name:
            iteration_results: dict[str, tuple[Iteration, IterationResult]] = {}

            for active_iteration in [cc.current_iteration for cc in campaign_group]:
                cohort_results: dict[str, CohortResult] = {}

                filter_rules, suppression_rules = self.get_rules_by_type(active_iteration)
                for cohort in sorted(active_iteration.iteration_cohorts, key=attrgetter("priority")):
                    # Base Eligibility - check
                    if cohort.cohort_label in self.person_cohorts or cohort.cohort_label == magic_cohort:
                        # Eligibility - check
                        if self.is_eligible_by_filter_rules(cohort, cohort_results, filter_rules):
                            # Actionability - evaluation
                            self.evaluate_suppression_rules(cohort, cohort_results, suppression_rules)

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
                iteration_results[active_iteration.name] = (active_iteration, IterationResult(status, best_cohorts))

            # Determine results between iterations - get the best
            if iteration_results:
                best_iteration_name, (best_active_iteration, best_candidate) = max(
                    iteration_results.items(), key=lambda item: item[1][1].status.value
                )
            else:
                best_candidate = IterationResult(eligibility.Status.not_eligible, [])
                best_active_iteration = None
            condition_results[condition_name] = best_candidate

            if best_candidate.status.actionable:
                redirect_rules, action_mapper, default_comms = self.get_redirect_rules(best_active_iteration)
                priority_getter = attrgetter("priority")
                sorted_rules_by_priority = sorted(redirect_rules, key=priority_getter)

                actions: list[Action] = self.get_actions_from_comms(self, action_mapper, default_comms)
                for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
                    rule_group_list = list(rule_group)
                    matcher_matched_list = [
                        getattr(RuleCalculator(person_data=self.person_data, rule=rule).evaluate_exclusion()[1],
                                "matcher_matched")
                        for rule in rule_group_list
                    ]

                    if all(matcher_matched_list):
                        actions = self.get_actions_from_comms(self, action_mapper, rule_group_list[0].comms_routing)
                        break

        #list_actions = [Action]
        #for action in actions:
        #    list_actions.append(Action(action.actionType, action.actionCode, action.actionDescription, action.urlLink))

        # Consolidate all the results and return
        final_result = [
            Condition(
                condition_name=condition_name,
                status=active_iteration_result.status,
                cohort_results=active_iteration_result.cohort_results,
                actions=actions
            )
            for condition_name, active_iteration_result in condition_results.items()
        ]
        return eligibility.EligibilityStatus(conditions=final_result)

    def is_eligible_by_filter_rules(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortResult],
        filter_rules: Iterable[rules.IterationRule],
    ) -> bool:
        is_eligible = True
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, filter_rules), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_inclusion_reasons, group_exclusion_reasons, rule_stop = self.evaluate_rules_priority_group(
                rule_group
            )
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
        cohort_results: dict[str, CohortResult],
        suppression_rules: Iterable[rules.IterationRule],
    ) -> None:
        is_actionable: bool = True
        priority_getter = attrgetter("priority")
        suppression_reasons = []

        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, suppression_rules), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_inclusion_reasons, group_exclusion_reasons, rule_stop = self.evaluate_rules_priority_group(
                rule_group
            )
            if status.is_exclusion:
                is_actionable = False
                suppression_reasons.extend(group_exclusion_reasons)
                if rule_stop:
                    break

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

    def evaluate_rules_priority_group(
        self, rules_group: Iterator[rules.IterationRule]
    ) -> tuple[eligibility.Status, list[eligibility.Reason], list[eligibility.Reason], bool]:
        is_rule_stop = False
        inclusion_reasons, exclusion_reasons = [], []
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
                inclusion_reasons.append(reason)

        return best_status, inclusion_reasons, exclusion_reasons, is_rule_stop

    @staticmethod
    def get_actions_from_comms(self, action_mapper: dict[str, dict[str, str]], comms: str) -> list[Action]:
        actions: list[Action] = []
        for comm in comms.split("|"):
            actions.append(Action(
                actionType=action_mapper.get(comm)["ActionType"],
                actionCode=action_mapper.get(comm)["ExternalRoutingCode"],
                actionDescription=action_mapper.get(comm)["ActionDescription"],
                urlLink=action_mapper.get(comm)["url_link"],
                  )
            )

        return actions
