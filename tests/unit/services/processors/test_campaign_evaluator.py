import datetime

import pytest
from hamcrest import assert_that, is_

from eligibility_signposting_api.model.rules import CampaignID
from eligibility_signposting_api.services.processors.campaign_evaluator import CampaignEvaluator
from tests.fixtures.builders.model import rule


@pytest.fixture
def campaign_evaluator():
    return CampaignEvaluator()


@pytest.mark.parametrize(
    ("campaign_target", "campaign_type", "conditions_filter", "category_filter", "expected_result"),
    [
        ("RSV", "V", ["RSV"], "VACCINATIONS", [("RSV", "V")]),
        ("RSV", "V", ["COVID"], "VACCINATIONS", []),
        ("RSV", "S", ["RSV"], "ALL", [("RSV", "S")]),
        ("RSV", "S", ["ALL"], "ALL", [("RSV", "S")]),
        ("RSV", "S", ["RSV"], "VACCINATIONS", []),
        ("RSV", "V", ["RSV"], "ALL", [("RSV", "V")]),
        ("FLU", "V", ["COVID", "RSV"], "ALL", []),
        ("FLU", "S", ["ALL"], "ALL", [("FLU", "S")]),
        ("COVID", "V", ["UNKNOWN"], "VACCINATIONS", []),
        ("FLU", "V", ["COVID", "FLU"], "VACCINATIONS", [("FLU", "V")]),
    ],
)
def test_campaigns_grouped_by_condition_name_filters_correctly(  # noqa: PLR0913
    campaign_evaluator, campaign_target, campaign_type, conditions_filter, category_filter, expected_result
):
    campaign = rule.CampaignConfigFactory.build(target=campaign_target, type=campaign_type)

    result = campaign_evaluator.get_requested_grouped_campaigns([campaign], conditions_filter, category_filter)
    assert_that([(str(name), group[0].type) for name, group in result], is_(expected_result))


def test_campaigns_grouped_by_condition_name_with_no_campaigns(campaign_evaluator):
    result = campaign_evaluator.get_requested_grouped_campaigns([], ["RSV"], "VACCINATIONS")
    assert_that(list(result), is_([]))


def test_campaigns_grouped_by_condition_name_with_no_active_campaigns(campaign_evaluator):
    campaign = rule.CampaignConfigFactory.build(
        target="RSV", type="V", start_date=datetime.date(2025, 4, 20), end_date=datetime.date(2025, 4, 21)
    )

    result = campaign_evaluator.get_requested_grouped_campaigns([campaign], ["RSV"], "VACCINATIONS")
    assert_that(list(result), is_([]))


@pytest.mark.parametrize(
    ("category_filter", "campaign_type", "expected_count"),
    [
        ("SCREENING", "S", 1),
        ("SCREENING", "V", 0),
        ("INVALID_CATEGORY", "S", 0),
    ],
)
def test_campaigns_grouped_by_condition_name_with_various_categories(
    campaign_evaluator, category_filter, campaign_type, expected_count
):
    campaign = rule.CampaignConfigFactory.build(target="COVID", type=campaign_type)
    result = list(campaign_evaluator.get_requested_grouped_campaigns([campaign], ["COVID"], category_filter))
    assert_that(len(result), is_(expected_count))
    if expected_count > 0:
        assert_that(str(result[0][0]), is_("COVID"))


def test_campaigns_grouped_by_condition_name_with_empty_conditions_filter(campaign_evaluator):
    campaign = rule.CampaignConfigFactory.build(target="RSV", type="V")
    result = campaign_evaluator.get_requested_grouped_campaigns([campaign], [], "VACCINATIONS")
    assert_that(list(result), is_([]))


def test_campaigns_grouped_by_condition_name_groups_multiple_campaigns_for_same_target(campaign_evaluator):
    campaign1 = rule.CampaignConfigFactory.build(target="COVID", type="V", id="C1")
    campaign2 = rule.CampaignConfigFactory.build(target="COVID", type="V", id="C2")
    campaign3 = rule.CampaignConfigFactory.build(target="FLU", type="V", id="F1")
    inactive_campaign = rule.CampaignConfigFactory.build(
        target="COVID", type="V", id="C3", start_date=datetime.date(2025, 4, 20), end_date=datetime.date(2025, 4, 21)
    )

    all_campaigns = [campaign1, campaign2, campaign3, inactive_campaign]
    result = list(campaign_evaluator.get_requested_grouped_campaigns(all_campaigns, ["COVID", "FLU"], "VACCINATIONS"))

    assert_that(len(result), is_(2))

    result_dict = {str(name): campaigns for name, campaigns in result}
    assert_that("COVID" in result_dict)
    assert_that("FLU" in result_dict)

    assert_that(len(result_dict["COVID"]), is_(2))
    assert_that({c.id for c in result_dict["COVID"]}, is_({CampaignID("C1"), CampaignID("C2")}))

    assert_that(len(result_dict["FLU"]), is_(1))
    assert_that(result_dict["FLU"][0].id, is_(CampaignID("F1")))


def test_campaign_grouping_is_affected_by_order_for_mixed_types(campaign_evaluator):
    campaign_v = rule.CampaignConfigFactory.build(target="RSV", type="V")
    campaign_s = rule.CampaignConfigFactory.build(target="RSV", type="S")

    evaluator_s_first = campaign_evaluator
    result_s_first = list(
        evaluator_s_first.get_requested_grouped_campaigns([campaign_s, campaign_v], ["RSV"], "VACCINATIONS")
    )
    assert_that(result_s_first, is_([]))

    evaluator_v_first = campaign_evaluator
    result_v_first = list(
        evaluator_v_first.get_requested_grouped_campaigns([campaign_v, campaign_s], ["RSV"], "VACCINATIONS")
    )
    assert_that(len(result_v_first), is_(1))
    assert_that(len(result_v_first[0][1]), is_(2))
