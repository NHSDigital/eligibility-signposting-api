from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from itertools import chain
from typing import TYPE_CHECKING, TypeVar

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
    Reason,
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
        IterationName,
    )
    from eligibility_signposting_api.model.person import Person


logger = logging.getLogger(__name__)
T = TypeVar("T")


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

            condition: Condition = self.build_condition(
                iteration_result=condition_results[condition_name], condition_name=condition_name
            )
            condition_with_replaced_tokens = EligibilityCalculator.find_and_replace_tokens_recursive(
                self.person, condition
            )

            final_result.append(condition_with_replaced_tokens)

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
            status_text=iteration_result.status.get_status_text(condition_name),
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

    @staticmethod
    def find_and_replace_tokens_recursive(person: Person, data_class: T) -> T:
        if not is_dataclass(data_class):
            return data_class

        for class_field in fields(data_class):
            value = getattr(data_class, class_field.name)

            if isinstance(value, str):
                setattr(data_class, class_field.name, EligibilityCalculator.replace_token(value, person))

            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if is_dataclass(item):
                        value[i] = EligibilityCalculator.find_and_replace_tokens_recursive(person, item)
                    elif isinstance(item, str):
                        value[i] = EligibilityCalculator.replace_token(item, person)

            elif is_dataclass(value):
                setattr(
                    data_class, class_field.name, EligibilityCalculator.find_and_replace_tokens_recursive(person, value)
                )

        return data_class

    @staticmethod
    def replace_token(text: str, person: Person) -> str:
        if not isinstance(text, str):
            return text

        pattern = r"\[\[.*?\]\]"
        date_pattern = r"\DATE\((.*?)\)"
        all_tokens = re.findall(pattern, text, re.IGNORECASE)

        for token in all_tokens:
            middle = token[2:-2]
            try:
                attribute_level = middle.split(".")[0].upper()
                attribute_name = middle.split(".")[1]
                replace_with = ""
                valid_person_keys = EligibilityCalculator.get_all_valid_person_keys(person)

                allowed_attribute_levels = ["PERSON", "TARGET"]
                for attribute in person.data:
                    if attribute_level not in allowed_attribute_levels:
                        raise ValueError(f"Invalid attribute level '{attribute_level}' in token '{token}'.")

                    if attribute_level == "PERSON" and attribute.get("ATTRIBUTE_TYPE") == "PERSON":
                        if attribute_name.split(":")[0].upper() in valid_person_keys:
                            replace_with = EligibilityCalculator.replace_with_formatting(
                                attribute, attribute_name, date_pattern, replace_with
                            )
                        else:
                            raise ValueError(f"Invalid attribute name '{attribute_name}' in token '{token}'.")

                    if attribute_level == "TARGET":
                        if attribute.get("ATTRIBUTE_TYPE") == attribute_name.upper():
                            attribute_value = middle.split(".")[2]
                            if attribute_value.split(":")[0].upper() in valid_person_keys:
                                replace_with = EligibilityCalculator.replace_with_formatting(
                                    attribute, attribute_value, date_pattern, replace_with
                                )
                            else:
                                raise ValueError(
                                    f"Invalid target attribute name '{attribute_value}' in token '{token}'."
                                )

                text = text.replace(token, str(replace_with))

            except ValueError as e:
                raise ValueError(e)

        return text

    @staticmethod
    def replace_with_formatting(attribute, attribute_value, date_pattern, replace_with):
        try:
            if len(attribute_value.split(":")) > 1:
                token_format_type = attribute_value.split(":")[1]
                token_date_format = re.search(date_pattern, token_format_type, re.IGNORECASE).group(1)
                unformatted_replace_with = attribute.get(attribute_value.split(":")[0].upper())
                if unformatted_replace_with is not None:
                    replace_with_date_object = datetime.strptime(str(unformatted_replace_with), "%Y%m%d")
                    replace_with = replace_with_date_object.strftime(str(token_date_format))
            else:
                replace_with = attribute.get(attribute_value) if attribute.get(attribute_value) else ""
            return replace_with
        except AttributeError:
            raise AttributeError("Invalid token format")

    @staticmethod
    def get_all_valid_person_keys(person: Person) -> set[str]:
        all_keys = set()
        for item in person.data:
            keys = item.keys()
            for key in keys:
                key.upper()
            all_keys.update(keys)
        return all_keys
