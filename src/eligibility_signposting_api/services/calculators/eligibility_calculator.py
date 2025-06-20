from __future__ import annotations

from _operator import attrgetter
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import groupby
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eligibility_signposting_api.model.rules import ActionsMapper, Iteration, IterationCohort

from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import (
    ActionCode,
    ActionDescription,
    ActionType,
    CohortGroupResult,
    Condition,
    ConditionName,
    IterationResult,
    Status,
    SuggestedAction,
    SuggestedActions,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.services.calculators.rule_calculator import (
    RuleCalculator,
)

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

    @property
    def active_campaigns(self) -> list[rules.CampaignConfig]:
        return [cc for cc in self.campaign_configs if cc.campaign_live]

    @property
    def campaigns_grouped_by_condition_name(
        self,
    ) -> Iterator[tuple[eligibility.ConditionName, list[rules.CampaignConfig]]]:
        """Generator function to iterate over campaign groups by condition name."""
        for condition_name, campaign_group in groupby(
            sorted(self.active_campaigns, key=attrgetter("target")),
            key=attrgetter("target"),
        ):
            yield condition_name, list(campaign_group)

    @property
    def person_cohorts(self) -> set[str]:
        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (row for row in self.person_data if row.get("ATTRIBUTE_TYPE") == "COHORTS"),
            {},
        )
        return set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

    @staticmethod
    def get_the_best_cohort_memberships(
        cohort_results: dict[str, CohortGroupResult],
    ) -> tuple[Status, list[CohortGroupResult]]:
        if not cohort_results:
            return eligibility.Status.not_eligible, []

        best_status = eligibility.Status.best(*[result.status for result in cohort_results.values()])
        best_cohorts = [result for result in cohort_results.values() if result.status == best_status]

        best_cohorts = [
            CohortGroupResult(
                cohort_code=cc.cohort_code,
                status=cc.status,
                reasons=cc.reasons,
                description=(cc.description or "").strip() if cc.description else "",
            )
            for cc in best_cohorts
        ]

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
    ) -> tuple[tuple[rules.IterationRule, ...], ActionsMapper, str]:
        redirect_rules = tuple(
            rule for rule in active_iteration.iteration_rules if rule.type in rules.RuleType.redirect
        )
        default_comms = active_iteration.default_comms_routing
        action_mapper = active_iteration.actions_mapper
        return redirect_rules, action_mapper, default_comms

    def evaluate_eligibility(self, *, include_actions_flag: bool = True) -> eligibility.EligibilityStatus:
        """Iterates over campaign groups, evaluates eligibility, and returns a consolidated status."""
        condition_results: dict[ConditionName, IterationResult] = {}
        actions: SuggestedActions | None = SuggestedActions([])

        for condition_name, campaign_group in self.campaigns_grouped_by_condition_name:
            iteration_results: dict[str, tuple[Iteration, IterationResult]] = {}

            for active_iteration in [cc.current_iteration for cc in campaign_group]:
                cohort_results: dict[str, CohortGroupResult] = self.get_cohort_results(active_iteration)

                # Determine Result between cohorts - get the best
                status, best_cohorts = self.get_the_best_cohort_memberships(cohort_results)
                iteration_results[active_iteration.name] = (
                    active_iteration,
                    IterationResult(status, best_cohorts, actions),
                )

            # Determine results between iterations - get the best
            if iteration_results:
                best_iteration_name, (best_active_iteration, best_candidate) = max(
                    iteration_results.items(), key=lambda item: item[1][1].status.value
                )
            else:
                best_candidate = IterationResult(eligibility.Status.not_eligible, [], actions)
                best_active_iteration = None
            condition_results[condition_name] = best_candidate

            if best_candidate.status == Status.actionable and best_active_iteration is not None:
                actions = self.handle_redirect_rules(best_active_iteration) if include_actions_flag else None
            if best_candidate.status in (Status.not_eligible, Status.not_actionable) and not include_actions_flag:
                actions = None

            # add actions to condition results
            condition_results[condition_name].actions = actions
        # Consolidate all the results and return
        final_result = self.build_condition_results(condition_results)
        return eligibility.EligibilityStatus(conditions=final_result)

    def handle_redirect_rules(self, best_active_iteration: Iteration) -> SuggestedActions | None:
        redirect_rules, action_mapper, default_comms = self.get_redirect_rules(best_active_iteration)
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(redirect_rules, key=priority_getter)

        actions: SuggestedActions | None = self.get_actions_from_comms(action_mapper, default_comms)
        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            rule_group_list = list(rule_group)
            matcher_matched_list = [
                RuleCalculator(person_data=self.person_data, rule=rule).evaluate_exclusion()[1].matcher_matched
                for rule in rule_group_list
            ]

            comms_routing = rule_group_list[0].comms_routing
            if comms_routing and all(matcher_matched_list):
                rule_actions = self.get_actions_from_comms(action_mapper, comms_routing)
                if rule_actions and len(rule_actions.actions) > 0:
                    actions = rule_actions
                break

        return actions

    def get_cohort_results(self, active_iteration: rules.Iteration) -> dict[str, CohortGroupResult]:
        cohort_results: dict[str, CohortGroupResult] = {}
        filter_rules, suppression_rules = self.get_rules_by_type(active_iteration)
        for cohort in sorted(active_iteration.iteration_cohorts, key=attrgetter("priority")):
            # Base Eligibility - check
            if cohort.cohort_label in self.person_cohorts or cohort.is_magic_cohort:
                # Eligibility - check
                if self.is_eligible_by_filter_rules(cohort, cohort_results, filter_rules):
                    # Actionability - evaluation
                    self.evaluate_suppression_rules(cohort, cohort_results, suppression_rules)

            # Not base eligible
            elif cohort.cohort_label is not None:
                cohort_results[cohort.cohort_label] = CohortGroupResult(
                    (cohort.cohort_group),
                    Status.not_eligible,
                    [],
                    cohort.negative_description,
                )
        return cohort_results

    @staticmethod
    def build_condition_results(condition_results: dict[ConditionName, IterationResult]) -> list[Condition]:
        conditions: list[Condition] = []
        # iterate over conditions
        for condition_name, active_iteration_result in condition_results.items():
            grouped_cohort_results = defaultdict(list)
            # iterate over cohorts and group them by status and cohort_group
            for cohort_result in active_iteration_result.cohort_results:
                if active_iteration_result.status == cohort_result.status:
                    grouped_cohort_results[cohort_result.cohort_code].append(cohort_result)

            # deduplicate grouped cohort results by cohort_code
            deduplicated_cohort_results = [
                CohortGroupResult(
                    cohort_code=group_cohort_code,
                    status=group[0].status,
                    # Flatten all reasons from the group
                    reasons=[reason for cohort in group for reason in cohort.reasons],
                    # get the first nonempty description
                    description=next((c.description for c in group if c.description), group[0].description),
                )
                for group_cohort_code, group in grouped_cohort_results.items()
                if group
            ]

            # return condition with cohort results
            conditions.append(
                Condition(
                    condition_name=condition_name,
                    status=active_iteration_result.status,
                    cohort_results=list(deduplicated_cohort_results),
                    actions=condition_results[condition_name].actions,
                )
            )
        return conditions

    def is_eligible_by_filter_rules(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
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
                    cohort_results[cohort.cohort_label] = CohortGroupResult(
                        (cohort.cohort_group),
                        Status.not_eligible,
                        [],
                        cohort.negative_description,
                    )
                is_eligible = False
                break
        return is_eligible

    def evaluate_suppression_rules(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
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
                cohort_results[key] = CohortGroupResult(
                    cohort.cohort_group,
                    Status.actionable,
                    [],
                    cohort.positive_description,
                )
            else:
                cohort_results[key] = CohortGroupResult(
                    cohort.cohort_group,
                    Status.not_actionable,
                    suppression_reasons,
                    cohort.positive_description,
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
    def get_actions_from_comms(action_mapper: ActionsMapper, comms: str) -> SuggestedActions | None:
        suggested_actions: SuggestedActions = SuggestedActions([])
        for comm in comms.split("|"):
            action = action_mapper.get(comm)
            if action is not None:
                suggested_actions.actions.append(
                    SuggestedAction(
                        action_type=ActionType(action.action_type),
                        action_code=ActionCode(action.action_code),
                        action_description=ActionDescription(action.action_description)
                        if action.action_description
                        else None,
                        url_link=UrlLink(action.url_link) if action.url_link else None,
                        url_label=UrlLabel(action.url_label) if action.url_label else None,
                    )
                )
        return suggested_actions
