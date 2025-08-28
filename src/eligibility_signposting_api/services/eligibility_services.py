import logging

from wireup import service

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.repos import CampaignRepo, NotFoundError, PersonRepo
from eligibility_signposting_api.services.calculators import eligibility_calculator as calculator

logger = logging.getLogger(__name__)


class UnknownPersonError(Exception):
    pass


class InvalidQueryParamError(Exception):
    pass


@service
class EligibilityService:
    def __init__(
        self,
        person_repo: PersonRepo,
        campaign_repo: CampaignRepo,
        calculator_factory: calculator.EligibilityCalculatorFactory,
    ) -> None:
        super().__init__()
        self.person_repo = person_repo
        self.campaign_repo = campaign_repo
        self.calculator_factory = calculator_factory

    def get_eligibility_status(
        self,
        nhs_number: eligibility_status.NHSNumber,
        include_actions: str,
        conditions: list[str],
        category: str,
    ) -> eligibility_status.EligibilityStatus:
        """Calculate a person's eligibility for vaccination given an NHS number."""
        if nhs_number:
            try:
                person_data = self.person_repo.get_eligibility_data(nhs_number)
                campaign_configs = list(self.campaign_repo.get_campaign_configs())
            except NotFoundError as e:
                raise UnknownPersonError from e
            else:
                calc: calculator.EligibilityCalculator = self.calculator_factory.get(person_data, campaign_configs)
                return calc.get_eligibility_status(include_actions, conditions, category)

        raise UnknownPersonError  # pragma: no cover
