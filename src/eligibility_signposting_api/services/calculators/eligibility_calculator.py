from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from eligibility_signposting_api.audit.audit_context import AuditContext
from eligibility_signposting_api.model.types import Row
from eligibility_signposting_api.services.calculators.action_rule_handler import ActionRuleHandler
from eligibility_signposting_api.services.calculators.campaign_processor import CampaignProcessor
from eligibility_signposting_api.services.calculators.cohort_evaluator import CohortEvaluator
from eligibility_signposting_api.services.calculators.eligibility_result_builder import EligibilityResultBuilder
from eligibility_signposting_api.services.calculators.person_data_reader import PersonDataReader

if TYPE_CHECKING:
    from eligibility_signposting_api.model.rules import (
        CampaignConfig,
        CampaignID,
        CampaignVersion,
        Iteration,
    )

from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import (
    CohortGroupResult,
    ConditionName,
    IterationResult,
    Status,
    SuggestedAction,
)

@service
class EligibilityCalculatorFactory:
    @staticmethod
    def get(person_data: Row, campaign_configs: Collection[rules.CampaignConfig]) -> EligibilityCalculator:
        person_data_reader = PersonDataReader(person_data)
        campaign_processor = CampaignProcessor(campaign_configs)
        cohort_evaluator = CohortEvaluator(person_data_reader=person_data_reader)
        action_rule_handler = ActionRuleHandler(person_data_reader=person_data_reader)

        return EligibilityCalculator(
            person_data=person_data,
            campaign_configs=campaign_configs,
            campaign_processor=campaign_processor,
            person_data_reader=person_data_reader,
            cohort_evaluator=cohort_evaluator,
            action_rule_handler=action_rule_handler,
        )


@dataclass
class EligibilityCalculator:
    person_data: Row
    campaign_configs: Collection[rules.CampaignConfig]

    campaign_processor: CampaignProcessor
    person_data_reader: PersonDataReader
    cohort_evaluator: CohortEvaluator
    action_rule_handler: ActionRuleHandler

    results: list[eligibility.Condition] = field(default_factory=list)

    def evaluate_eligibility(
        self, include_actions: str, conditions: list[str], category: str
    ) -> eligibility.EligibilityStatus:
        include_actions_flag = include_actions.upper() == "Y"
        condition_results: dict[ConditionName, IterationResult] = {}
        actions: list[SuggestedAction] | None = []
        action_rule_priority, action_rule_name = None, None

        for condition_name, campaign_group in self.campaign_processor.get_campaigns_grouped_by_condition_name(
            conditions, category
        ):
            best_active_iteration: Iteration | None
            best_candidate: IterationResult
            best_campaign_id: CampaignID | None
            best_campaign_version: CampaignVersion | None
            best_cohort_results: dict[str, CohortGroupResult] | None

            iteration_results = self.get_iteration_results(actions, campaign_group)

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
                    actions, matched_action_rule_priority, matched_action_rule_name = (
                        self.action_rule_handler.handle_action_rules(best_active_iteration, rule_type)
                    )
                    action_rule_name = matched_action_rule_name
                    action_rule_priority = matched_action_rule_priority
                else:
                    actions = None
            else:
                actions = None

            if best_candidate.status in (Status.not_eligible, Status.not_actionable) and not include_actions_flag:
                actions = None

            condition_results[condition_name].actions = actions

            actions: list[SuggestedAction] | None = []

            AuditContext.append_audit_condition(
                condition_results[condition_name].actions,
                condition_name,
                (best_active_iteration, best_candidate, best_cohort_results),
                (best_campaign_id, best_campaign_version),
                (action_rule_priority, action_rule_name),
            )

        final_result = EligibilityResultBuilder.build_condition_results(condition_results)
        return eligibility.EligibilityStatus(conditions=final_result)

    def get_iteration_results(
        self, actions: list[SuggestedAction] | None, campaign_group: list[CampaignConfig]
    ) -> dict[str, tuple[Iteration, IterationResult, CampaignID, CampaignVersion, dict[str, CohortGroupResult]]]:
        iteration_results: dict[
            str, tuple[Iteration, IterationResult, CampaignID, CampaignVersion, dict[str, CohortGroupResult]]
        ] = {}
        for cc in campaign_group:
            active_iteration = cc.current_iteration
            cohort_results: dict[str, CohortGroupResult] = self.cohort_evaluator.get_cohort_results(active_iteration)

            status, best_cohorts = self.cohort_evaluator.get_the_best_cohort_memberships(cohort_results)
            iteration_results[active_iteration.name] = (
                active_iteration,
                IterationResult(status, best_cohorts, actions),
                cc.id,
                cc.version,
                cohort_results,
            )
        return iteration_results
