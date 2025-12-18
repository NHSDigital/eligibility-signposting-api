import logging

from wireup import service

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import CampaignConfig
from eligibility_signposting_api.repos import CampaignRepo, NotFoundError, PersonRepo
from eligibility_signposting_api.repos.consumer_mapping_repo import ConsumerMappingRepo
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
        consumer_mapping_repo: ConsumerMappingRepo
    ) -> None:
        super().__init__()
        self.person_repo = person_repo
        self.campaign_repo = campaign_repo
        self.calculator_factory = calculator_factory
        self.consumer_mapping = consumer_mapping_repo

    def get_eligibility_status(
        self,
        nhs_number: eligibility_status.NHSNumber,
        include_actions: str,
        conditions: list[str],
        category: str,
        consumer_id: str,
    ) -> eligibility_status.EligibilityStatus:
        """Calculate a person's eligibility for vaccination given an NHS number."""
        if nhs_number:
            try:
                person_data = self.person_repo.get_eligibility_data(nhs_number)
                campaign_configs = list(self.campaign_repo.get_campaign_configs())
                permitted_campaign_ids = self.consumer_mapping.get_permitted_campaign_ids(consumer_id)
                permitted_campaign_configs: list[CampaignConfig] = [
                    campaign for campaign in campaign_configs
                    if campaign.id in permitted_campaign_ids
                ]

            except NotFoundError as e:
                raise UnknownPersonError from e
            else:
                calc: calculator.EligibilityCalculator = self.calculator_factory.get(person_data,
                                                                                     permitted_campaign_configs)
                return calc.get_eligibility_status(include_actions, conditions, category)

        raise UnknownPersonError  # pragma: no cover
