from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from wireup import service

from eligibility_signposting_api.audit.audit_context import AuditContext
from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.eligibility_status import (
    BestIterationResult,
    CohortGroupResult,
    Condition,
    ConditionName,
    EligibilityStatus,
    IterationResult,
    Status,
)
from eligibility_signposting_api.services.processors.action_rule_handler import ActionRuleHandler
from eligibility_signposting_api.services.processors.campaign_evaluator import CampaignEvaluator
from eligibility_signposting_api.services.processors.rule_processor import RuleProcessor

if TYPE_CHECKING:
    from collections.abc import Collection

    from eligibility_signposting_api.model.campaign_config import (
        CampaignConfig,
        CohortLabel,
        IterationName, RuleType,
)
    from eligibility_signposting_api.model.person import Person

logger = logging.getLogger(__name__)


@service
class EligibilityCalculatorFactory:
    @staticmethod
    def get(person: Person, campaign_configs: Collection[CampaignConfig]) -> EligibilityCalculator:
        return EligibilityCalculator(person=person, campaign_configs=campaign_configs)


@dataclass
class EligibilityCalculator:
    person: Person
    campaign_configs: Collection[CampaignConfig]

    campaign_evaluator: CampaignEvaluator = field(default_factory=CampaignEvaluator)
    rule_processor: RuleProcessor = field(default_factory=RuleProcessor)
    action_rule_handler: ActionRuleHandler = field(default_factory=ActionRuleHandler)

    results: list[eligibility_status.Condition] = field(default_factory=list)

    @staticmethod
    def get_the_best_cohort_memberships(
        cohort_results: dict[CohortLabel, CohortGroupResult],
    ) -> tuple[Status, list[CohortGroupResult]]:
        if not cohort_results:
            return eligibility_status.Status.not_eligible, []

        best_status = eligibility_status.Status.best(*[result.status for result in cohort_results.values()])
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

    def get_eligibility_status(self, include_actions: str, conditions: list[str], category: str) -> EligibilityStatus:
        include_actions_flag = include_actions.upper() == "Y"
        condition_results: dict[ConditionName, IterationResult] = {}
        final_result = []

        requested_grouped_campaigns = self.campaign_evaluator.get_requested_grouped_campaigns(
            self.campaign_configs, conditions, category
        )
        for condition_name, campaign_group in requested_grouped_campaigns:
            best_iteration_result = self.get_best_iteration_result(campaign_group)

            if best_iteration_result is None:
                continue

            matched_action_detail = self.action_rule_handler.get_actions(
                self.person,
                best_iteration_result.active_iteration,
                best_iteration_result.iteration_result,
                include_actions_flag=include_actions_flag,
            )

            condition_results[condition_name] = best_iteration_result.iteration_result
            condition_results[condition_name].actions = matched_action_detail.actions

            condition_result = self.build_condition_results(condition_results[condition_name], condition_name)
            final_result.append(condition_result)

            AuditContext.append_audit_condition(
                condition_name,
                best_iteration_result,
                matched_action_detail,
                condition_results[condition_name].cohort_results,
            )

        # Consolidate all the results and return
        return eligibility_status.EligibilityStatus(conditions=final_result)

    def get_best_iteration_result(self, campaign_group: list[CampaignConfig]) -> BestIterationResult | None:
        iteration_results = self.get_iteration_results(campaign_group)

        if not iteration_results:
            return None

        (best_iteration_name, best_iteration_result) = max(
            iteration_results.items(),
            key=lambda item: next(iter(item[1].cohort_results.values())).status.value
            # Below handles the case where there are no cohort results
            if item[1].cohort_results
            else -1,
        )

        return best_iteration_result

    def get_iteration_results(self, campaign_group: list[CampaignConfig]) -> dict[IterationName, BestIterationResult]:
        iteration_results: dict[IterationName, BestIterationResult] = {}

        for cc in campaign_group:
            try:
                active_iteration = cc.current_iteration
            except StopIteration:
                logger.info("Skipping campaign ID %s as no active iteration was found.", cc.id)
                continue
            cohort_results: dict[CohortLabel, CohortGroupResult] = self.rule_processor.get_cohort_group_results(
                self.person, active_iteration
            )

            # Determine Result between cohorts - get the best
            status, best_cohorts = self.get_the_best_cohort_memberships(cohort_results)
            iteration_results[active_iteration.name] = BestIterationResult(
                IterationResult(status, best_cohorts, []), active_iteration, cc.id, cc.version, cohort_results
            )
        return iteration_results

    @staticmethod
    def build_condition_results(iteration_result: IterationResult, condition_name: ConditionName) -> Condition:
        grouped_cohort_results = defaultdict(list)

        for cohort_result in iteration_result.cohort_results:
            if iteration_result.status == cohort_result.status:
                grouped_cohort_results[cohort_result.cohort_code].append(cohort_result)

        deduplicated_cohort_results = []

        for group_cohort_code, group in grouped_cohort_results.items():
            if group:
                unique_rule_codes = set()
                deduplicated_reasons = []
                for cohort in group:
                    for reason in cohort.reasons:
                        if reason.rule_priority not in unique_rule_codes and reason.rule_description:
                            unique_rule_codes.add(reason.rule_priority)
                            deduplicated_reasons.append(reason)

                non_empty_description = next((c.description for c in group if c.description), group[0].description)
                cohort_group_result = CohortGroupResult(
                    cohort_code=group_cohort_code,
                    status=group[0].status,
                    reasons=deduplicated_reasons,
                    description=non_empty_description,
                    audit_rules=[],
                )
                deduplicated_cohort_results.append(cohort_group_result)

        return Condition(
            condition_name=condition_name,
            status=iteration_result.status,
            cohort_results=list(deduplicated_cohort_results),
            actions=iteration_result.actions,
            status_text=iteration_result.status.get_status_text(condition_name),
        )
