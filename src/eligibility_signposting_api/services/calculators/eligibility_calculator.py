from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING

from wireup import service

from eligibility_signposting_api.audit.audit_context import AuditContext
from eligibility_signposting_api.model import campaign_config, eligibility_status
from eligibility_signposting_api.model.eligibility_status import (
    BestIterationResult,
    CohortGroupResult,
    Condition,
    ConditionName,
    EligibilityStatus,
    IterationResult,
    Reason,
    Status,
    StatusText,
)
from eligibility_signposting_api.services.processors.action_rule_handler import ActionRuleHandler
from eligibility_signposting_api.services.processors.campaign_evaluator import CampaignEvaluator
from eligibility_signposting_api.services.processors.rule_processor import RuleProcessor
from eligibility_signposting_api.services.processors.token_processor import TokenProcessor

if TYPE_CHECKING:
    from collections.abc import Collection

    from eligibility_signposting_api.model.campaign_config import (
        CampaignConfig,
        CohortLabel,
        IterationName,
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

            best_iteration_result = TokenProcessor.find_and_replace_tokens(self.person, best_iteration_result)
            matched_action_detail = TokenProcessor.find_and_replace_tokens(self.person, matched_action_detail)

            condition_results[condition_name] = best_iteration_result.iteration_result
            condition_results[condition_name].actions = matched_action_detail.actions

            condition: Condition = self.build_condition(
                iteration_result=condition_results[condition_name], condition_name=condition_name
            )

            final_result.append(condition)

            AuditContext.append_audit_condition(
                condition_name,
                best_iteration_result,
                matched_action_detail,
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
            status_text = self.get_status_text(active_iteration.status_text, ConditionName(cc.target), status)

            iteration_results[active_iteration.name] = BestIterationResult(
                IterationResult(status, status_text, best_cohorts, []),
                active_iteration,
                cc.id,
                cc.version,
                cohort_results,
            )
        return iteration_results

    @staticmethod
    def get_status_text(
        status_text: campaign_config.StatusText | None, condition_name: ConditionName, status: Status
    ) -> StatusText:
        if status_text is None:
            status_text_or_default = status.get_default_status_text(condition_name)
        else:
            status_to_text = {
                Status.not_eligible: status_text.not_eligible
                or Status.not_eligible.get_default_status_text(condition_name),
                Status.not_actionable: status_text.not_actionable
                or Status.not_actionable.get_default_status_text(condition_name),
                Status.actionable: status_text.actionable or Status.actionable.get_default_status_text(condition_name),
            }
            status_text_or_default = StatusText(status_to_text[status])
        return status_text_or_default

    @staticmethod
    def build_condition(iteration_result: IterationResult, condition_name: ConditionName) -> Condition:
        grouped_cohort_results = defaultdict(list)

        for cohort_result in iteration_result.cohort_results:
            if iteration_result.status == cohort_result.status:
                grouped_cohort_results[cohort_result.cohort_code].append(cohort_result)

        deduplicated_cohort_results: list[CohortGroupResult] = EligibilityCalculator.deduplicate_cohort_results(
            grouped_cohort_results
        )

        overall_deduplicated_reasons_for_condition = EligibilityCalculator.deduplicate_reasons(
            deduplicated_cohort_results
        )

        return Condition(
            condition_name=condition_name,
            status=iteration_result.status,
            cohort_results=list(deduplicated_cohort_results),
            suitability_rules=list(overall_deduplicated_reasons_for_condition),
            actions=iteration_result.actions,
            status_text=iteration_result.status_text,
        )

    @staticmethod
    def deduplicate_cohort_results(
        grouped_cohort_results: dict[str, list[CohortGroupResult]],
    ) -> list[CohortGroupResult]:
        results = []

        for cohort_code, group_results in grouped_cohort_results.items():
            if not group_results:
                continue

            deduped_reasons: list[Reason] = EligibilityCalculator.deduplicate_reasons(group_results)

            description = next((c.description for c in group_results if c.description), group_results[0].description)

            results.append(
                CohortGroupResult(
                    cohort_code=cohort_code,
                    status=group_results[0].status,
                    reasons=list(deduped_reasons),
                    description=description,
                    audit_rules=[],
                )
            )

        return results

    @staticmethod
    def deduplicate_reasons(group_results: list[CohortGroupResult]) -> list[Reason]:
        all_reasons = chain.from_iterable(group_result.reasons for group_result in group_results)
        deduped = {}
        for reason in all_reasons:
            key = (reason.rule_type, reason.rule_priority)
            deduped.setdefault(key, reason)
        return list(deduped.values())
