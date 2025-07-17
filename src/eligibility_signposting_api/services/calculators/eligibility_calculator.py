from __future__ import annotations

from _operator import attrgetter
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import groupby
from typing import TYPE_CHECKING, Any

from eligibility_signposting_api.audit.audit_context import AuditContext

if TYPE_CHECKING:
    from eligibility_signposting_api.model.rules import (
        ActionsMapper,
        CampaignConfig,
        CampaignID,
        CampaignVersion,
        Iteration,
        IterationCohort,
        RuleName,
        RulePriority,
        RuleType,
    )

from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import (
    ActionCode,
    ActionDescription,
    ActionType,
    CohortGroupResult,
    Condition,
    ConditionName,
    InternalActionCode,
    IterationResult,
    Status,
    SuggestedAction,
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

    def campaigns_grouped_by_condition_name(
        self, conditions: list[str], category: str
    ) -> Iterator[tuple[eligibility.ConditionName, list[rules.CampaignConfig]]]:
        """Generator that yields campaign groups filtered by condition names and campaign category."""

        mapping = {
            "ALL": {"V", "S"},
            "VACCINATIONS": {"V"},
            "SCREENING": {"S"},
        }

        allowed_types = mapping.get(category, set())

        filter_all_conditions = "ALL" in conditions

        for condition_name, campaign_group in groupby(
            sorted(self.active_campaigns, key=attrgetter("target")),
            key=attrgetter("target"),
        ):
            campaigns = list(campaign_group)
            if campaigns[0].type in allowed_types and (filter_all_conditions or str(condition_name) in conditions):
                yield condition_name, campaigns

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
                audit_rules=cc.audit_rules,
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
    def get_action_rules_components(
        active_iteration: Iteration, rule_type: RuleType
    ) -> tuple[tuple[rules.IterationRule, ...], ActionsMapper, str | None]:
        action_rules = tuple(rule for rule in active_iteration.iteration_rules if rule.type in rule_type)

        routing_map = {
            rules.RuleType.redirect: active_iteration.default_comms_routing,
            rules.RuleType.not_eligible_actions: active_iteration.default_not_eligible_routing,
            rules.RuleType.not_actionable_actions: active_iteration.default_not_actionable_routing,
        }

        default_comms = routing_map.get(rule_type)
        action_mapper = active_iteration.actions_mapper
        return action_rules, action_mapper, default_comms

    def evaluate_eligibility(
        self, include_actions: str, conditions: list[str], category: str
    ) -> eligibility.EligibilityStatus:
        include_actions_flag = include_actions.upper() == "Y"
        condition_results: dict[ConditionName, IterationResult] = {}
        actions: list[SuggestedAction] | None = []
        action_rule_priority, action_rule_name = None, None

        for condition_name, campaign_group in self.campaigns_grouped_by_condition_name(conditions, category):
            best_active_iteration: Iteration | None
            best_candidate: IterationResult
            best_campaign_id: CampaignID | None
            best_campaign_version: CampaignVersion | None
            best_cohort_results: dict[str, CohortGroupResult] | None

            iteration_results = self.get_iteration_results(actions, campaign_group)

            # Determine results between iterations - get the best
            if iteration_results:
                (
                    best_iteration_name,
                    (
                        best_active_iteration,
                        best_candidate,
                        best_campaign_id,
                        best_campaign_version,
                        best_cohort_results,
                    ),
                ) = max(iteration_results.items(), key=lambda item: item[1][1].status.value)
            else:
                best_candidate = IterationResult(eligibility.Status.not_eligible, [], actions)
                best_campaign_id = None
                best_campaign_version = None
                best_active_iteration = None
                best_cohort_results = None

            condition_results[condition_name] = best_candidate

            status_to_rule_type = {
                Status.actionable: rules.RuleType.redirect,
                Status.not_eligible: rules.RuleType.not_eligible_actions,
                Status.not_actionable: rules.RuleType.not_actionable_actions,
            }

            if best_candidate.status in status_to_rule_type and best_active_iteration is not None:
                if include_actions_flag:
                    rule_type = status_to_rule_type[best_candidate.status]
                    actions, matched_action_rule_priority, matched_action_rule_name = self.handle_action_rules(
                        best_active_iteration, rule_type
                    )
                    action_rule_name = matched_action_rule_name
                    action_rule_priority = matched_action_rule_priority
                else:
                    actions = None

            else:
                actions = None

            if best_candidate.status in (Status.not_eligible, Status.not_actionable) and not include_actions_flag:
                actions = None

            # add actions to condition results
            condition_results[condition_name].actions = actions
            # reset actions for the next condition
            actions: list[SuggestedAction] | None = []

            # add audit data
            AuditContext.append_audit_condition(
                condition_results[condition_name].actions,
                condition_name,
                (best_active_iteration, best_candidate, best_cohort_results),
                (best_campaign_id, best_campaign_version),
                (action_rule_priority, action_rule_name),
            )

        # Consolidate all the results and return
        final_result = self.build_condition_results(condition_results)
        return eligibility.EligibilityStatus(conditions=final_result)

    def get_iteration_results(
        self, actions: list[SuggestedAction] | None, campaign_group: list[CampaignConfig]
    ) -> dict[str, tuple[Iteration, IterationResult, CampaignID, CampaignVersion, dict[str, CohortGroupResult]]]:
        iteration_results: dict[
            str, tuple[Iteration, IterationResult, CampaignID, CampaignVersion, dict[str, CohortGroupResult]]
        ] = {}
        for cc in campaign_group:
            active_iteration = cc.current_iteration
            cohort_results: dict[str, CohortGroupResult] = self.get_cohort_results(active_iteration)

            # Determine Result between cohorts - get the best
            status, best_cohorts = self.get_the_best_cohort_memberships(cohort_results)
            iteration_results[active_iteration.name] = (
                active_iteration,
                IterationResult(status, best_cohorts, actions),
                cc.id,
                cc.version,
                cohort_results,
            )
        return iteration_results

    def handle_action_rules(
        self, best_active_iteration: Iteration, rule_type: RuleType
    ) -> tuple[list[SuggestedAction] | None, RulePriority | None, RuleName | None]:
        action_rules, action_mapper, default_comms = self.get_action_rules_components(best_active_iteration, rule_type)
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(action_rules, key=priority_getter)

        actions: list[SuggestedAction] | None = self.get_actions_from_comms(action_mapper, default_comms)  # pyright: ignore[reportArgumentType]

        matched_action_rule_priority, matched_action_rule_name = None, None
        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            rule_group_list = list(rule_group)
            matcher_matched_list = [
                RuleCalculator(person_data=self.person_data, rule=rule).evaluate_exclusion()[1].matcher_matched
                for rule in rule_group_list
            ]

            comms_routing = rule_group_list[0].comms_routing
            if comms_routing and all(matcher_matched_list):
                rule_actions = self.get_actions_from_comms(action_mapper, comms_routing)
                if rule_actions and len(rule_actions) > 0:
                    actions = rule_actions
                matched_action_rule_priority = rule_group_list[0].priority
                matched_action_rule_name = rule_group_list[0].name
                break

        return actions, matched_action_rule_priority, matched_action_rule_name

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
                    cohort.cohort_group,
                    Status.not_eligible,
                    [],
                    cohort.negative_description,
                    [],
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
                    audit_rules=[],
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
                    status_text=active_iteration_result.status.get_status_text(condition_name),
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
            status, group_exclusion_reasons, _ = self.evaluate_rules_priority_group(rule_group)
            if status.is_exclusion:
                if cohort.cohort_label is not None:
                    cohort_results[cohort.cohort_label] = CohortGroupResult(
                        (cohort.cohort_group),
                        Status.not_eligible,
                        [],
                        cohort.negative_description,
                        group_exclusion_reasons,
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
            status, group_exclusion_reasons, rule_stop = self.evaluate_rules_priority_group(rule_group)
            if status.is_exclusion:
                is_actionable = False
                suppression_reasons.extend(group_exclusion_reasons)
                if rule_stop:
                    break

        if cohort.cohort_label is not None:
            key = cohort.cohort_label
            if is_actionable:
                cohort_results[key] = CohortGroupResult(
                    cohort.cohort_group, Status.actionable, [], cohort.positive_description, suppression_reasons
                )
            else:
                cohort_results[key] = CohortGroupResult(
                    cohort.cohort_group,
                    Status.not_actionable,
                    suppression_reasons,
                    cohort.positive_description,
                    suppression_reasons,
                )

    def evaluate_rules_priority_group(
        self, rules_group: Iterator[rules.IterationRule]
    ) -> tuple[eligibility.Status, list[eligibility.Reason], bool]:
        is_rule_stop = False
        exclusion_reasons = []
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

        return best_status, exclusion_reasons, is_rule_stop

    @staticmethod
    def get_actions_from_comms(action_mapper: ActionsMapper, comms: str) -> list[SuggestedAction] | None:
        suggested_actions: list[SuggestedAction] = []
        for comm in comms.split("|"):
            action = action_mapper.get(comm)
            if action is not None:
                suggested_actions.append(
                    SuggestedAction(
                        internal_action_code=InternalActionCode(comm),
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
