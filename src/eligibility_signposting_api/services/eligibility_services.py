import logging
from collections import defaultdict
from collections.abc import Collection, Iterator, Mapping
from itertools import groupby
from operator import attrgetter
from typing import Any

from hamcrest.core.string_description import StringDescription
from wireup import service

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.repos import CampaignRepo, NotFoundError, PersonRepo
from eligibility_signposting_api.services.rules.operators import OperatorRegistry

logger = logging.getLogger(__name__)


class UnknownPersonError(Exception):
    pass


@service
class EligibilityService:
    def __init__(self, person_repo: PersonRepo, campaign_repo: CampaignRepo) -> None:
        super().__init__()
        self.person_repo = person_repo
        self.campaign_repo = campaign_repo

    def get_eligibility_status(self, nhs_number: eligibility.NHSNumber | None = None) -> eligibility.EligibilityStatus:
        """Calculate a person's eligibility for vaccination given an NHS number."""
        if nhs_number:
            try:
                person_data = self.person_repo.get_eligibility_data(nhs_number)
                campaign_configs = list(self.campaign_repo.get_campaign_configs())
                logger.debug(
                    "got person_data for %r",
                    nhs_number,
                    extra={
                        "campaign_configs": [c.model_dump(by_alias=True) for c in campaign_configs],
                        "person_data": person_data,
                        "nhs_number": nhs_number,
                    },
                )
            except NotFoundError as e:
                raise UnknownPersonError from e
            else:
                return self.evaluate_eligibility(campaign_configs, person_data)

        raise UnknownPersonError  # pragma: no cover

    @staticmethod
    def evaluate_eligibility(
        campaign_configs: Collection[rules.CampaignConfig], person_data: Collection[Mapping[str, Any]]
    ) -> eligibility.EligibilityStatus:
        """Calculate a person's eligibility for vaccination."""

        # Get all iterations for which the person is base eligible, i.e. those which *might* provide eligibility
        # due to cohort membership.
        base_eligible_campaigns, condition_names = EligibilityService.get_base_eligible_campaigns(
            campaign_configs, person_data
        )
        # Evaluate iteration rules to see if the person is actionable, not actionable (due to "F" rules),
        # or not eligible (due to "S" rules")
        evaluations = EligibilityService.evaluate_for_base_eligible_campaigns(base_eligible_campaigns, person_data)

        conditions: dict[eligibility.ConditionName, eligibility.Condition] = {}
        # Add all not base eligible conditions to result set.
        conditions |= EligibilityService.get_not_base_eligible_conditions(base_eligible_campaigns, condition_names)
        # Add all base eligible conditions to result set.
        conditions |= EligibilityService.get_base_eligible_conditions(evaluations)

        return eligibility.EligibilityStatus(conditions=list(conditions.values()))

    @staticmethod
    def get_base_eligible_campaigns(
        campaign_configs: Collection[rules.CampaignConfig], person_data: Collection[Mapping[str, Any]]
    ) -> tuple[list[rules.CampaignConfig], set[eligibility.ConditionName]]:
        """Get all campaigns for which the person is base eligible, i.e. those which *might* provide eligibility.

        Build and return a collection of campaigns for which the person is base eligible (using cohorts).
        Also build and return a set of conditions in the campaigns while we are here.
        """
        condition_names: set[eligibility.ConditionName] = set()
        base_eligible_campaigns: list[rules.CampaignConfig] = []

        for campaign_config in (cc for cc in campaign_configs if cc.campaign_live and cc.current_iteration):
            condition_name = eligibility.ConditionName(campaign_config.target)
            condition_names.add(condition_name)
            base_eligible = EligibilityService.evaluate_base_eligibility(campaign_config.current_iteration, person_data)
            if base_eligible:
                base_eligible_campaigns.append(campaign_config)

        return base_eligible_campaigns, condition_names

    @staticmethod
    def evaluate_base_eligibility(
        iteration: rules.Iteration | None, person_data: Collection[Mapping[str, Any]]
    ) -> set[str]:
        """Return cohorts for which person is base eligible."""
        if not iteration:
            return set()
        iteration_cohorts: set[str] = {
            cohort.cohort_label for cohort in iteration.iteration_cohorts if cohort.cohort_label
        }

        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (r for r in person_data if r.get("ATTRIBUTE_TYPE", "") == "COHORTS"), {}
        )
        person_cohorts = set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

        return iteration_cohorts.intersection(person_cohorts)

    @staticmethod
    def get_not_base_eligible_conditions(
        base_eligible_campaigns: Collection[rules.CampaignConfig],
        condition_names: Collection[eligibility.ConditionName],
    ) -> dict[eligibility.ConditionName, eligibility.Condition]:
        """Get conditions where the person is not base eligible,
        i.e. is not is the cohort for any campaign iteration."""

        # for each condition:
        # if the person isn't base eligible for any iteration,
        #         the person is not (base) eligible for the condition
        not_eligible_conditions: dict[eligibility.ConditionName, eligibility.Condition] = {}
        for condition_name in condition_names:
            if condition_name not in {eligibility.ConditionName(cc.target) for cc in base_eligible_campaigns}:
                not_eligible_conditions[condition_name] = eligibility.Condition(
                    condition_name=condition_name, status=eligibility.Status.not_eligible, reasons=[]
                )
        return not_eligible_conditions

    @staticmethod
    def evaluate_for_base_eligible_campaigns(
        base_eligible_campaigns: Collection[rules.CampaignConfig],
        person_data: Collection[Mapping[str, Any]],
    ) -> dict[eligibility.ConditionName, dict[eligibility.Status, list[eligibility.Reason]]]:
        """Evaluate iteration rules to see if the person is actionable, not actionable (due to "F" rules),
        or not eligible (due to "S" rules").

        For each condition, evaluate all iterations for inclusion or exclusion."""
        priority_getter = attrgetter("priority")

        base_eligible_evaluations: dict[
            eligibility.ConditionName, dict[eligibility.Status, list[eligibility.Reason]]
        ] = defaultdict(dict)
        for condition_name, iteration in [
            (eligibility.ConditionName(cc.target), cc.current_iteration)
            for cc in base_eligible_campaigns
            if cc.current_iteration
        ]:
            # Until we see a worse status, we assume someone is actionable for this iteration.
            worst_status_so_far_for_condition = eligibility.Status.actionable
            exclusion_reasons, actionable_reasons = [], []
            for _priority, iteration_rule_group in groupby(
                sorted(iteration.iteration_rules, key=priority_getter), key=priority_getter
            ):
                worst_status_so_far_for_condition, group_actionable_reasons, group_exclusion_reasons = (
                    EligibilityService.evaluate_priority_group(
                        iteration_rule_group, person_data, worst_status_so_far_for_condition
                    )
                )
                actionable_reasons.extend(group_actionable_reasons)
                exclusion_reasons.extend(group_exclusion_reasons)
            condition_entry = base_eligible_evaluations.setdefault(condition_name, {})
            condition_status_entry = condition_entry.setdefault(worst_status_so_far_for_condition, [])
            condition_status_entry.extend(
                actionable_reasons
                if worst_status_so_far_for_condition is eligibility.Status.actionable
                else exclusion_reasons
            )
        return base_eligible_evaluations

    @staticmethod
    def evaluate_priority_group(
        iteration_rule_group: Iterator[rules.IterationRule],
        person_data: Collection[Mapping[str, Any]],
        worst_status_so_far_for_condition: eligibility.Status,
    ) -> tuple[eligibility.Status, list[eligibility.Reason], list[eligibility.Reason]]:
        actionable_reasons, exclusion_reasons = [], []
        exclude_capable_rules = [
            ir for ir in iteration_rule_group if ir.type in (rules.RuleType.filter, rules.RuleType.suppression)
        ]
        best_status_so_far_for_priority_group = (
            eligibility.Status.not_eligible if exclude_capable_rules else eligibility.Status.actionable
        )
        for iteration_rule in exclude_capable_rules:
            exclusion, reason = EligibilityService.evaluate_exclusion(iteration_rule, person_data)
            if exclusion:
                best_status_so_far_for_priority_group = EligibilityService.best_status(
                    iteration_rule.type, best_status_so_far_for_priority_group
                )
                exclusion_reasons.append(reason)
            else:
                best_status_so_far_for_priority_group = eligibility.Status.actionable
                actionable_reasons.append(reason)
        return (
            EligibilityService.worst_status(best_status_so_far_for_priority_group, worst_status_so_far_for_condition),
            actionable_reasons,
            exclusion_reasons,
        )

    @staticmethod
    def worst_status(*statuses: eligibility.Status) -> eligibility.Status:
        """Pick the worst status from those given.

        Here "worst" means furthest from being able to access vaccination, so not-eligible is "worse" than
        not-actionable, and not-actionable is "worse" than actionable.
        """
        return min(statuses)

    @staticmethod
    def best_status(rule_type: rules.RuleType, status: eligibility.Status) -> eligibility.Status:
        """Pick the best status between the existing status, and the status implied by
        the rule excluding the person from vaccination.

        Here "best" means closest to being able to access vaccination, so not-actionable is "better" than
        not-eligible, and actionable is "better" than not-actionable.
        """
        return max(
            status,
            eligibility.Status.not_eligible
            if rule_type == rules.RuleType.filter
            else eligibility.Status.not_actionable,
        )

    @staticmethod
    def get_base_eligible_conditions(
        base_eligible_evaluations: Mapping[
            eligibility.ConditionName, Mapping[eligibility.Status, list[eligibility.Reason]]
        ],
    ) -> dict[eligibility.ConditionName, eligibility.Condition]:
        """Get conditions where the person is base eligible, but may be either actionable, not actionable,
        or not eligible."""

        # for each condition for which the person is base eligible:
        #   what is the "best" status, i.e. closest to actionable? Add the condition to the result with that status.
        eligible_conditions: dict[eligibility.ConditionName, eligibility.Condition] = {}
        for condition_name, reasons_by_status in base_eligible_evaluations.items():
            best_status = max(reasons_by_status.keys())
            eligible_conditions[condition_name] = eligibility.Condition(
                condition_name=condition_name, status=best_status, reasons=reasons_by_status[best_status]
            )
        return eligible_conditions

    @staticmethod
    def evaluate_exclusion(
        iteration_rule: rules.IterationRule, person_data: Collection[Mapping[str, str | None]]
    ) -> tuple[bool, eligibility.Reason]:
        """Evaluate if a particular rule excludes this person. Return the result, and the reason for the result."""
        attribute_value = EligibilityService.get_attribute_value(iteration_rule, person_data)
        exclusion, reason = EligibilityService.evaluate_rule(iteration_rule, attribute_value)
        reason = eligibility.Reason(
            rule_name=eligibility.RuleName(iteration_rule.name),
            rule_type=eligibility.RuleType(iteration_rule.type),
            rule_result=eligibility.RuleResult(
                f"Rule {iteration_rule.name!r} ({iteration_rule.description!r}) "
                f"{'' if exclusion else 'not '}excluding - "
                f"{iteration_rule.attribute_name!r} {iteration_rule.comparator!r} {reason}"
            ),
        )
        return exclusion, reason

    @staticmethod
    def get_attribute_value(
        iteration_rule: rules.IterationRule, person_data: Collection[Mapping[str, str | None]]
    ) -> str | None:
        """Pull out the correct attribute for a rule from the person's data."""
        match iteration_rule.attribute_level:
            case rules.RuleAttributeLevel.PERSON:
                person: Mapping[str, str | None] | None = next(
                    (r for r in person_data if r.get("ATTRIBUTE_TYPE", "") == "PERSON"), None
                )
                attribute_value = person.get(iteration_rule.attribute_name) if person else None
            case _:  # pragma: no cover
                msg = f"{iteration_rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    @staticmethod
    def evaluate_rule(iteration_rule: rules.IterationRule, attribute_value: str | None) -> tuple[bool, str]:
        """Evaluate a rule against a person data attribute. Return the result, and the reason for the result."""
        matcher_class = OperatorRegistry.get(iteration_rule.operator)
        matcher = matcher_class(rule_value=iteration_rule.comparator)

        reason = StringDescription()
        if matcher.matches(attribute_value):
            matcher.describe_match(attribute_value, reason)
            return True, str(reason)
        matcher.describe_mismatch(attribute_value, reason)
        return False, str(reason)
