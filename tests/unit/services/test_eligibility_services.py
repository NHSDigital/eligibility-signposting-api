from unittest.mock import MagicMock

import pytest
from hamcrest import assert_that, empty

from eligibility_signposting_api.model.campaign_config import CampaignConfig, CampaignID
from eligibility_signposting_api.model.eligibility_status import NHSNumber
from eligibility_signposting_api.repos import CampaignRepo, NotFoundError, PersonRepo
from eligibility_signposting_api.repos.consumer_mapping_repo import ConsumerMappingRepo
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from eligibility_signposting_api.services.calculators.eligibility_calculator import EligibilityCalculatorFactory
from tests.fixtures.matchers.eligibility import is_eligibility_status


@pytest.fixture
def mock_repos():
    return {
        "person": MagicMock(spec=PersonRepo),
        "campaign": MagicMock(spec=CampaignRepo),
        "consumer": MagicMock(spec=ConsumerMappingRepo),
        "factory": MagicMock(spec=EligibilityCalculatorFactory),
    }


@pytest.fixture
def service(mock_repos):
    return EligibilityService(
        mock_repos["person"], mock_repos["campaign"], mock_repos["consumer"], mock_repos["factory"]
    )


def test_eligibility_service_returns_from_repo():
    # Given
    person_repo = MagicMock(spec=PersonRepo)
    campaign_repo = MagicMock(spec=CampaignRepo)
    consumer_mapping_repo = MagicMock(spec=ConsumerMappingRepo)
    person_repo.get_eligibility = MagicMock(return_value=[])
    service = EligibilityService(person_repo, campaign_repo, consumer_mapping_repo, EligibilityCalculatorFactory())

    # When
    actual = service.get_eligibility_status(
        NHSNumber("1234567890"), include_actions="Y", conditions=["ALL"], category="ALL", consumer_id="test_consumer_id"
    )

    # Then
    assert_that(actual, is_eligibility_status().with_conditions(empty()))


def test_eligibility_service_for_nonexistent_nhs_number():
    # Given
    person_repo = MagicMock(spec=PersonRepo)
    campaign_repo = MagicMock(spec=CampaignRepo)
    consumer_mapping_repo = MagicMock(spec=ConsumerMappingRepo)
    person_repo.get_eligibility_data = MagicMock(side_effect=NotFoundError)
    service = EligibilityService(person_repo, campaign_repo, consumer_mapping_repo, EligibilityCalculatorFactory())

    # When
    with pytest.raises(UnknownPersonError):
        service.get_eligibility_status(
            NHSNumber("1234567890"),
            include_actions="Y",
            conditions=["ALL"],
            category="ALL",
            consumer_id="test_consumer_id",
        )


def test_get_eligibility_status_filters_permitted_campaigns(service, mock_repos):
    """Tests that ONLY permitted campaigns reach the calculator factory."""
    # Given
    nhs_number = NHSNumber("1234567890")
    person_data = {"age": 65, "vulnerable": True}
    mock_repos["person"].get_eligibility_data.return_value = person_data

    # Available campaigns in system
    camp_a = MagicMock(spec=CampaignConfig, id=CampaignID("CAMP_A"))
    camp_b = MagicMock(spec=CampaignConfig, id=CampaignID("CAMP_B"))
    mock_repos["campaign"].get_campaign_configs.return_value = [camp_a, camp_b]

    # Consumer is only permitted to see CAMP_B
    mock_repos["consumer"].get_permitted_campaign_ids.return_value = [CampaignID("CAMP_B")]

    # Mock calculator behavior
    mock_calc = MagicMock()
    mock_repos["factory"].get.return_value = mock_calc
    mock_calc.get_eligibility_status.return_value = "eligible_result"

    # When
    result = service.get_eligibility_status(nhs_number, "Y", ["FLU"], "G1", "consumer_xyz")

    # Then
    # Verify the factory was called ONLY with camp_b
    mock_repos["factory"].get.assert_called_once_with(person_data, [camp_b])
    assert result == "eligible_result"


def test_raises_unknown_person_error_on_repo_not_found(service, mock_repos):
    """Tests that NotFoundError from repo is translated to UnknownPersonError."""
    mock_repos["person"].get_eligibility_data.side_effect = NotFoundError

    with pytest.raises(UnknownPersonError):
        service.get_eligibility_status(NHSNumber("999"), "Y", [], "", "any")
