import logging
from collections import OrderedDict, defaultdict
from collections.abc import Collection, Mapping
from typing import Any

from hamcrest.core.string_description import StringDescription
from wireup import service

from eligibility_signposting_api.model import eligibility
from eligibility_signposting_api.model.rules import CampaignConfig, Iteration, IterationRule, RuleAttributeLevel
from eligibility_signposting_api.repos import EligibilityRepo, NotFoundError, RulesRepo
from eligibility_signposting_api.services.rules.operators import OperatorRegistry

logger = logging.getLogger(__name__)


class UnknownPersonError(Exception):
    pass


@service
class EligibilityService:
    def __init__(self, eligibility_repo: EligibilityRepo, rules_repo: RulesRepo) -> None:
        super().__init__()
        self.eligibility_repo = eligibility_repo
        self.rules_repo = rules_repo

    def get_eligibility_status(self, nhs_number: eligibility.NHSNumber | None = None) -> eligibility.EligibilityStatus:
        """Calculate a person's eligibility for vaccination given an NHS number."""
        if nhs_number:
            try:
                person_data = self.eligibility_repo.get_eligibility_data(nhs_number)
                campaign_configs = list(self.rules_repo.get_campaign_configs())
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
        campaign_configs: Collection[CampaignConfig], person_data: Collection[Mapping[str, Any]]
    ) -> eligibility.EligibilityStatus:
        """Calculate a person's eligibility for vaccination."""

        # Get all iterations for which the person is base eligible, i.e. those which *might* provide eligibility.
        base_eligible_iterations, condition_names = EligibilityService.get_base_eligibility_iterations(
            campaign_configs, person_data
        )
        # Evaluate iteration rules to see if the person is actionable
        base_eligible_evaluations = EligibilityService.evaluate_for_base_eligible_iterations(
            base_eligible_iterations, person_data
        )

        conditions: dict[eligibility.ConditionName, eligibility.Condition] = {}
        # Add all not eligible conditions to result set.
        conditions |= EligibilityService.get_not_eligible_conditions(base_eligible_iterations, condition_names)
        # Add all actionable and not actionable conditions to result set.
        conditions |= EligibilityService.get_eligible_conditions(base_eligible_evaluations)

        return eligibility.EligibilityStatus(conditions=list(conditions.values()))

    @staticmethod
    def get_base_eligibility_iterations(
        campaign_configs: Collection[CampaignConfig], person_data: Collection[Mapping[str, Any]]
    ) -> tuple[OrderedDict[eligibility.ConditionName, Iteration], set[eligibility.ConditionName]]:
        """Get all iterations for which the person is base eligible, i.e. those which *might* provide eligibility.

        Build and return a collection of campaign iterations for which the person is base eligible (using cohorts).
        Also build and return a set of conditions in the campaigns while we are here.
        """
        condition_names: set[eligibility.ConditionName] = set()
        base_eligible_iterations: OrderedDict[eligibility.ConditionName, Iteration] = OrderedDict()
        for campaign_config in campaign_configs:
            condition_name = eligibility.ConditionName(campaign_config.target)
            condition_names.add(condition_name)
            for iteration in campaign_config.iterations:
                base_eligible = EligibilityService.evaluate_base_eligibility(iteration, person_data)
                if base_eligible:
                    base_eligible_iterations[condition_name] = iteration
        return base_eligible_iterations, condition_names

    @staticmethod
    def evaluate_base_eligibility(iteration: Iteration, person_data: Collection[Mapping[str, Any]]) -> set[str]:
        """Return cohorts for which person is base eligible."""
        iteration_cohorts: set[str] = {
            cohort.cohort_label for cohort in iteration.iteration_cohorts if cohort.cohort_label
        }

        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (r for r in person_data if r.get("ATTRIBUTE_TYPE", "") == "COHORTS"), {}
        )
        person_cohorts = set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

        return iteration_cohorts.intersection(person_cohorts)

    @staticmethod
    def get_not_eligible_conditions(
        base_eligible_iterations: Mapping[eligibility.ConditionName, Iteration],
        condition_names: Collection[eligibility.ConditionName],
    ) -> dict[eligibility.ConditionName, eligibility.Condition]:
        """Get conditions where the person is not base eligible,
        i.e. is not is the cohort for any campaign iteration."""

        # for each condition:
        # if the person isn't base eligible for any iteration,
        #         the person is not (base) eligible for the condition
        not_eligible_conditions: dict[eligibility.ConditionName, eligibility.Condition] = {}
        for condition_name in condition_names:
            if condition_name not in base_eligible_iterations:
                not_eligible_conditions[condition_name] = eligibility.Condition(
                    condition_name=condition_name, status=eligibility.Status.not_eligible, reasons=[]
                )
        return not_eligible_conditions

    @staticmethod
    def evaluate_for_base_eligible_iterations(
        base_eligible_iterations: Mapping[eligibility.ConditionName, Iteration],
        person_data: Collection[Mapping[str, Any]],
    ) -> dict[eligibility.ConditionName, dict[eligibility.Status, list[eligibility.Reason]]]:
        """Evaluate iteration rules to see if the person is actionable.

        For each condition, evaluate all iterations for inclusion or exclusion."""

        # for each iteration for which the person is base eligible:
        #   if the person is excluded by any rules
        #     the person is not actionable for that iteration
        #   else
        #     the person is actionable for that iteration
        base_eligible_evaluations: dict[
            eligibility.ConditionName, dict[eligibility.Status, list[eligibility.Reason]]
        ] = defaultdict(dict)
        for condition_name, iteration in base_eligible_iterations.items():
            status = eligibility.Status.actionable
            exclusion_reasons, actionable_reasons = [], []
            for iteration_rule in iteration.iteration_rules:
                exclusion, reason = EligibilityService.evaluate_exclusion(iteration_rule, person_data)
                if exclusion:
                    status = eligibility.Status.not_actionable
                    exclusion_reasons.append(reason)
                else:
                    actionable_reasons.append(reason)
            condition_entry = base_eligible_evaluations.setdefault(condition_name, {})
            condition_status_entry = condition_entry.setdefault(status, [])
            condition_status_entry.extend(
                actionable_reasons if status is eligibility.Status.actionable else exclusion_reasons
            )
        return base_eligible_evaluations

    @staticmethod
    def get_eligible_conditions(
        base_eligible_evaluations: Mapping[
            eligibility.ConditionName, Mapping[eligibility.Status, list[eligibility.Reason]]
        ],
    ) -> dict[eligibility.ConditionName, eligibility.Condition]:
        """Get conditions where the person is either actionable or not actionable."""

        # for each condition for which the person is base eligible:
        #   if the person is actionable for *any* iteration?
        #     the person is actionable for the condition
        #   else
        #     the person is not actionable for the condition
        eligible_conditions: dict[eligibility.ConditionName, eligibility.Condition] = {}
        for condition_name, reasons_by_status in base_eligible_evaluations.items():
            if reasons := reasons_by_status.get(eligibility.Status.actionable, []):
                eligible_conditions[condition_name] = eligibility.Condition(
                    condition_name=condition_name,
                    status=eligibility.Status.actionable,
                    reasons=reasons,
                )
            else:
                eligible_conditions[condition_name] = eligibility.Condition(
                    condition_name=condition_name,
                    status=eligibility.Status.not_actionable,
                    reasons=reasons_by_status[eligibility.Status.not_actionable],
                )
        return eligible_conditions

    @staticmethod
    def evaluate_exclusion(
        iteration_rule: IterationRule, person_data: Collection[Mapping[str, str | None]]
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
        iteration_rule: IterationRule, person_data: Collection[Mapping[str, str | None]]
    ) -> str | None:
        """Pull out the correct attribute for a rule from the person's data."""
        match iteration_rule.attribute_level:
            case RuleAttributeLevel.PERSON:
                person: Mapping[str, str | None] | None = next(
                    (r for r in person_data if r.get("ATTRIBUTE_TYPE", "") == "PERSON"), None
                )
                attribute_value = person.get(iteration_rule.attribute_name) if person else None
            case _:  # pragma: no cover
                msg = f"{iteration_rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    @staticmethod
    def evaluate_rule(iteration_rule: IterationRule, attribute_value: str | None) -> tuple[bool, str]:
        """Evaluate a rule against a person data attribute. Return the result, and the reason for the result."""
        matcher_class = OperatorRegistry.get(iteration_rule.operator)
        matcher = matcher_class(rule_value=iteration_rule.comparator)

        reason = StringDescription()
        if matcher.matches(attribute_value):
            matcher.describe_match(attribute_value, reason)
            return True, str(reason)
        matcher.describe_mismatch(attribute_value, reason)
        return False, str(reason)
