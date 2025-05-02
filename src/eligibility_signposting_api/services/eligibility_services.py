import logging

from hamcrest.core.string_description import StringDescription
from wireup import service

from eligibility_signposting_api.model import eligibility
from eligibility_signposting_api.model.rules import CampaignConfig, IterationRule, RuleAttributeLevel
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
                # TODO: Apply rules here  # noqa: TD002, TD003, FIX002
                return self.evaluate_eligibility(campaign_configs, person_data)

        raise UnknownPersonError  # pragma: no cover

    @staticmethod
    def evaluate_eligibility(
        campaign_configs: list[CampaignConfig], person_data: list[dict[str, str | None]]
    ) -> eligibility.EligibilityStatus:
        """Calculate a person's eligibility for vaccination."""
        conditions: dict[eligibility.ConditionName, eligibility.Condition] = {}
        for campaign_config in campaign_configs:
            condition_name = eligibility.ConditionName(campaign_config.target)
            condition = conditions.setdefault(
                condition_name,
                eligibility.Condition(condition_name=condition_name, status=eligibility.Status.actionable, reasons=[]),
            )
            for iteration_rule in [
                iteration_rule
                for iteration in campaign_config.iterations
                for iteration_rule in iteration.iteration_rules
            ]:
                exclusion, reason = EligibilityService.evaluate_exclusion(iteration_rule, person_data)
                condition.reasons.append(
                    eligibility.Reason(
                        rule_type=eligibility.RuleType(iteration_rule.type),
                        rule_name=eligibility.RuleName(iteration_rule.name),
                        rule_result=eligibility.RuleResult(reason),
                    )
                )
                if exclusion:
                    condition.status = eligibility.Status.not_actionable

        return eligibility.EligibilityStatus(conditions=list(conditions.values()))

    @staticmethod
    def evaluate_exclusion(iteration_rule: IterationRule, person_data: list[dict[str, str | None]]) -> tuple[bool, str]:
        """Evaluate if a particular rule excludes this person. Return the result, and the reason for the result."""
        attribute_value = EligibilityService.get_attribute_value(iteration_rule, person_data)
        exclusion, reason = EligibilityService.evaluate_rule(iteration_rule, attribute_value)
        reason = (
            f"Rule {iteration_rule.name!r} ({iteration_rule.description!r}) "
            f"{'' if exclusion else 'not '}excluding - "
            f"{iteration_rule.attribute_name!r} {iteration_rule.comparator!r} {reason}"
        )
        return exclusion, reason

    @staticmethod
    def get_attribute_value(iteration_rule: IterationRule, person_data: list[dict[str, str | None]]) -> str | None:
        """Pull out the correct attribute for a rule from the person's data."""
        match iteration_rule.attribute_level:
            case RuleAttributeLevel.PERSON:
                person: dict[str, str | None] | None = next(
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
        matcher = matcher_class(iteration_rule.comparator)

        reason = StringDescription()
        if matcher.matches(attribute_value):
            matcher.describe_match(attribute_value, reason)
            return True, str(reason)
        matcher.describe_mismatch(attribute_value, reason)
        return False, str(reason)
