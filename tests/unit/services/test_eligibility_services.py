from unittest.mock import MagicMock

import pytest
from hamcrest import assert_that, empty

from eligibility_signposting_api.model.eligibility_status import NHSNumber
from eligibility_signposting_api.repos import CampaignRepo, NotFoundError, PersonRepo
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.services.calculators.eligibility_calculator import EligibilityCalculatorFactory
from tests.fixtures.matchers.eligibility import is_eligibility_status


def test_eligibility_service_returns_from_repo():
    # Given
    person_repo = MagicMock(spec=PersonRepo)
    campaign_repo = MagicMock(spec=CampaignRepo)
    person_repo.get_eligibility = MagicMock(return_value=[])
    service = EligibilityService(person_repo, campaign_repo, EligibilityCalculatorFactory())

    # When
    actual = service.get_eligibility_status(
        NHSNumber("1234567890"), include_actions="Y", conditions=["ALL"], category="ALL"
    )

    # Then
    assert_that(actual, is_eligibility_status().with_conditions(empty()))


def test_eligibility_service_for_nonexistent_nhs_number():
    # Given
    person_repo = MagicMock(spec=PersonRepo)
    campaign_repo = MagicMock(spec=CampaignRepo)
    person_repo.get_eligibility_data = MagicMock(side_effect=NotFoundError)
    service = EligibilityService(person_repo, campaign_repo, EligibilityCalculatorFactory())

    # When
    with pytest.raises(UnknownPersonError):
        service.get_eligibility_status(NHSNumber("1234567890"), include_actions="Y", conditions=["ALL"], category="ALL")
