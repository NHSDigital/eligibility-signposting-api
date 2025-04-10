import logging
from datetime import datetime
from typing import Any

from dateutil.relativedelta import relativedelta
from wireup import service

from eligibility_signposting_api.model.eligibility import EligibilityStatus, NHSNumber
from eligibility_signposting_api.model.rules import CampaignConfig, IterationRule, RuleAttributeLevel, RuleOperator
from eligibility_signposting_api.repos import EligibilityRepo, NotFoundError, RulesRepo

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
        campaign_configs: list[CampaignConfig], person_data: list[dict[str, Any]]
    ) -> EligibilityStatus:
        eligible, reasons, actions = True, [], []
        for iteration_rule in [
            iteration_rule
            for campaign_config in campaign_configs
            for iteration in campaign_config.iterations
            for iteration_rule in iteration.iteration_rules
        ]:
            if EligibilityService.evaluate_exclusion(iteration_rule, person_data):
                eligible = False

        return EligibilityStatus(eligible=eligible, reasons=reasons, actions=actions)

    @staticmethod
    def evaluate_exclusion(iteration_rule: IterationRule, person_data: list[dict[str, Any]]) -> bool:
        attribute_value = EligibilityService.get_attribute_value(iteration_rule, person_data)
        return EligibilityService.evaluate_rule(iteration_rule, attribute_value)

    @staticmethod
    def get_attribute_value(iteration_rule: IterationRule, person_data: list[dict[str, Any]]) -> Any:  # noqa: ANN401
        match iteration_rule.attribute_level:
            case RuleAttributeLevel.PERSON:
                person: dict[str, Any] | None = next(
                    (r for r in person_data if r.get("ATTRIBUTE_TYPE", "").startswith("PERSON")), None
                )
                attribute_value = person.get(iteration_rule.attribute_name) if person else None
            case _:
                msg = f"{iteration_rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    @staticmethod
    def evaluate_rule(iteration_rule: IterationRule, attribute_value: Any) -> bool:  # noqa: PLR0911, ANN401
        match iteration_rule.operator:
            case RuleOperator.equals:
                return attribute_value == iteration_rule.comparator
            case RuleOperator.ne:
                return attribute_value != iteration_rule.comparator
            case RuleOperator.lt:
                return attribute_value < iteration_rule.comparator
            case RuleOperator.lte:
                return attribute_value <= iteration_rule.comparator
            case RuleOperator.gt:
                return attribute_value > iteration_rule.comparator
            case RuleOperator.gte:
                return attribute_value >= iteration_rule.comparator
            case RuleOperator.year_gt:
                attribute_date = datetime.strptime(str(attribute_value), "%Y%m%d")  # noqa: DTZ007
                today = datetime.today()  # noqa: DTZ002
                cutoff = today + relativedelta(years=int(iteration_rule.comparator))
                return (attribute_date > cutoff) if attribute_value else False
            case _:
                msg = f"{iteration_rule.operator} not implemented"
                raise NotImplementedError(msg)
