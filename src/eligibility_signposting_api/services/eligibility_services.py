import logging

from wireup import service

from eligibility_signposting_api.model.eligibility import Condition, ConditionName, EligibilityStatus, NHSNumber, Status
from eligibility_signposting_api.model.rules import CampaignConfig, IterationRule, RuleAttributeLevel
from eligibility_signposting_api.repos import EligibilityRepo, NotFoundError, RulesRepo
from eligibility_signposting_api.services.rules.operators import OperatorRegistry

PersonData = str | None
logger = logging.getLogger(__name__)


class UnknownPersonError(Exception):
    pass


@service
class EligibilityService:
    def __init__(self, eligibility_repo: EligibilityRepo, rules_repo: RulesRepo) -> None:
        super().__init__()
        self.eligibility_repo = eligibility_repo
        self.rules_repo = rules_repo

    def get_eligibility_status(self, nhs_number: NHSNumber | None = None) -> EligibilityStatus:
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

        raise UnknownPersonError

    @staticmethod
    def evaluate_eligibility(
        campaign_configs: list[CampaignConfig], person_data: list[dict[str, PersonData]]
    ) -> EligibilityStatus:
        """Calculate a person's eligibility for vaccination."""
        conditions: dict[ConditionName, Condition] = {}
        for campaign_config in campaign_configs:
            condition_name = ConditionName(campaign_config.target)
            condition = conditions.setdefault(
                condition_name, Condition(condition_name=condition_name, status=Status.actionable)
            )
            for iteration_rule in [
                iteration_rule
                for iteration in campaign_config.iterations
                for iteration_rule in iteration.iteration_rules
            ]:
                if EligibilityService.evaluate_exclusion(iteration_rule, person_data):
                    condition.status = Status.not_actionable

        return EligibilityStatus(conditions=list(conditions.values()))

    @staticmethod
    def evaluate_exclusion(iteration_rule: IterationRule, person_data: list[dict[str, PersonData]]) -> bool:
        attribute_value = EligibilityService.get_attribute_value(iteration_rule, person_data)
        return EligibilityService.evaluate_rule(iteration_rule, attribute_value)

    @staticmethod
    def get_attribute_value(iteration_rule: IterationRule, person_data: list[dict[str, PersonData]]) -> PersonData:
        match iteration_rule.attribute_level:
            case RuleAttributeLevel.PERSON:
                person: dict[str, PersonData] | None = next(
                    (r for r in person_data if r.get("ATTRIBUTE_TYPE", "") == "PERSON"), None
                )
                attribute_value = person.get(iteration_rule.attribute_name) if person else None
            case _:
                msg = f"{iteration_rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    @staticmethod
    def evaluate_rule(iteration_rule: IterationRule, attribute_value: PersonData) -> bool:
        matcher_class = OperatorRegistry.get(iteration_rule.operator)
        return matcher_class(iteration_rule.comparator).matches(attribute_value)
