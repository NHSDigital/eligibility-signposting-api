import pytest
from dateutil.relativedelta import relativedelta
from faker import Faker

from tests.fixtures.builders.model.rule import IterationFactory, IterationRuleFactory, RawCampaignConfigFactory


def test_campaign_must_have_at_least_one_iteration():
    # Given

    # When, Then
    with pytest.raises(
        ValueError,
        match=r"1 validation error for CampaignConfig\n"
        r"iterations\n"
        r".*List should have at least 1 item",
    ):
        RawCampaignConfigFactory.build(iterations=[])


def test_campaign_start_date_must_be_before_end_date(faker: Faker):
    # Given
    start_date = faker.date_object()
    end_date = start_date - relativedelta(days=1)

    # When, Then
    with pytest.raises(
        ValueError,
        match=r"1 validation error for CampaignConfig\n"
        r".*start date .* after end date",
    ):
        RawCampaignConfigFactory.build(start_date=start_date, end_date=end_date)


def test_iteration_with_overlapping_start_dates_not_allowed(faker: Faker):
    # Given
    start_date = faker.date_object()
    iteration1 = IterationFactory.build(iteration_date=start_date)
    iteration2 = IterationFactory.build(iteration_date=start_date)

    # When, Then
    with pytest.raises(
        ValueError,
        match=r"1 validation error for CampaignConfig\n"
        r".*2 iterations with iteration date",
    ):
        RawCampaignConfigFactory.build(start_date=start_date, iterations=[iteration1, iteration2])


def test_iteration_must_have_active_iteration_from_its_start(faker: Faker):
    # Given
    start_date = faker.date_object()
    iteration = IterationFactory.build(iteration_date=start_date + relativedelta(days=1))

    # When, Then
    with pytest.raises(
        ValueError,
        match=r"1 validation error for CampaignConfig\n"
        r".*1st iteration starts later",
    ):
        RawCampaignConfigFactory.build(start_date=start_date, iterations=[iteration])


@pytest.mark.parametrize(
    ("rule_stop", "expected"),
    [
        ("Y", True),
        ("N", False),
        ("", False),
        (None, False),
    ],
)
def test_rules_stop_in_iteration_rules_assigns_yn_to_bool(rule_stop: str, expected):
    # Given, When
    iteration_rules = IterationRuleFactory.build(rule_stop=rule_stop)

    # Then
    assert iteration_rules.rule_stop is expected
