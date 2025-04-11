from datetime import datetime
from unittest.mock import MagicMock

import pytest
from brunns.matchers.object import false, true
from dateutil.relativedelta import relativedelta
from faker import Faker
from hamcrest import assert_that

from eligibility_signposting_api.model.eligibility import DateOfBirth, NHSNumber, Postcode
from eligibility_signposting_api.model.rules import RuleAttributeLevel, RuleOperator, RuleType
from eligibility_signposting_api.repos import EligibilityRepo, NotFoundError, RulesRepo
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from tests.utils.builders import CampaignConfigFactory, IterationFactory, IterationRuleFactory
from tests.utils.matchers.eligibility import is_eligibility_status


@pytest.fixture(scope="session")
def faker() -> Faker:
    return Faker("en_UK")


def test_eligibility_service_returns_from_repo():
    # Given
    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility = MagicMock(return_value=[])
    ps = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = ps.get_eligibility_status(NHSNumber("1234567890"))

    # Then
    assert_that(actual, is_eligibility_status().with_eligible(true()))


def test_eligibility_service_for_nonexistent_nhs_number():
    # Given
    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(side_effect=NotFoundError)
    ps = EligibilityService(eligibility_repo, rules_repo)

    # When
    with pytest.raises(UnknownPersonError):
        ps.get_eligibility_status(NHSNumber("1234567890"))


def test_simple_rule_eligible(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=79))
    postcode = Postcode(faker.postcode())

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=[
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": f"PERSON#{nhs_number}",
                "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
                "POSTCODE": postcode,
            }
        ]
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    IterationFactory.build(
                        iteration_rules=[
                            IterationRuleFactory.build(
                                type=RuleType.filter,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.year_gt,
                                comparator="-75",
                            ),
                            IterationRuleFactory.build(
                                type=RuleType.filter,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.lt,
                                comparator="19440902",
                            ),
                        ]
                    )
                ],
            )
        ]
    )

    ps = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = ps.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(actual, is_eligibility_status().with_eligible(true()))


def test_simple_rule_ineligible(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(maximum_age=74))
    postcode = Postcode(faker.postcode())

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=[
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": f"PERSON#{nhs_number}",
                "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
                "POSTCODE": postcode,
            }
        ]
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    IterationFactory.build(
                        iteration_rules=[
                            IterationRuleFactory.build(
                                type=RuleType.filter,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.year_gt,
                                comparator="-75",
                            ),
                            IterationRuleFactory.build(
                                type=RuleType.filter,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.lt,
                                comparator="19440902",
                            ),
                        ]
                    )
                ],
            )
        ]
    )

    ps = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = ps.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(actual, is_eligibility_status().with_eligible(false()))


def test_equals_rule():
    rule = IterationRuleFactory.build(operator=RuleOperator.equals, comparator="42")
    assert EligibilityService.evaluate_rule(rule, "42")
    assert not EligibilityService.evaluate_rule(rule, "99")


def test_not_equals_rule():
    rule = IterationRuleFactory.build(operator=RuleOperator.ne, comparator="42")
    assert EligibilityService.evaluate_rule(rule, "99")
    assert not EligibilityService.evaluate_rule(rule, "42")


def test_less_than_rule():
    rule = IterationRuleFactory.build(operator=RuleOperator.lt, comparator="100")
    assert EligibilityService.evaluate_rule(rule, "42")
    assert EligibilityService.evaluate_rule(rule, "99")
    assert not EligibilityService.evaluate_rule(rule, "100")
    assert not EligibilityService.evaluate_rule(rule, "101")


def test_less_than_or_equal_rule():
    rule = IterationRuleFactory.build(operator=RuleOperator.lte, comparator="100")
    assert EligibilityService.evaluate_rule(rule, "99")
    assert EligibilityService.evaluate_rule(rule, "100")
    assert not EligibilityService.evaluate_rule(rule, "101")


def test_greater_than_rule():
    rule = IterationRuleFactory.build(operator=RuleOperator.gt, comparator="100")
    assert EligibilityService.evaluate_rule(rule, "101")
    assert not EligibilityService.evaluate_rule(rule, "100")
    assert not EligibilityService.evaluate_rule(rule, "99")


def test_greater_than_or_equal_rule():
    rule = IterationRuleFactory.build(operator=RuleOperator.gte, comparator="100")
    assert EligibilityService.evaluate_rule(rule, "100")
    assert EligibilityService.evaluate_rule(rule, "101")
    assert not EligibilityService.evaluate_rule(rule, "99")


def test_year_gt_rule_future_date():
    today = datetime.today()  # noqa: DTZ002
    years_offset = 2
    future_date = today + relativedelta(years=years_offset + 1)
    attribute_value = future_date.strftime("%Y%m%d")
    rule = IterationRuleFactory.build(operator=RuleOperator.year_gt, comparator=str(years_offset))
    assert EligibilityService.evaluate_rule(rule, attribute_value)


def test_year_gt_rule_past_date():
    today = datetime.today()  # noqa: DTZ002
    years_offset = 2
    past_date = today + relativedelta(years=years_offset - 1)
    attribute_value = past_date.strftime("%Y%m%d")
    rule = IterationRuleFactory.build(operator=RuleOperator.year_gt, comparator=str(years_offset))
    assert not EligibilityService.evaluate_rule(rule, attribute_value)


def test_year_gt_rule_empty_value():
    rule = IterationRuleFactory.build(operator=RuleOperator.year_gt, comparator="2")
    assert not EligibilityService.evaluate_rule(rule, None)
    assert not EligibilityService.evaluate_rule(rule, "")


def test_unimplemented_operator():
    rule = IterationRuleFactory.build(operator=RuleOperator.member_of, comparator="something")
    with pytest.raises(NotImplementedError, match="not implemented"):
        EligibilityService.evaluate_rule(rule, "any_value")
