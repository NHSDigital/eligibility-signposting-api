from unittest.mock import MagicMock

import pytest
from faker import Faker
from hamcrest import assert_that, empty, has_item

from eligibility_signposting_api.model.eligibility import ConditionName, DateOfBirth, NHSNumber, Postcode, Status
from eligibility_signposting_api.model.rules import RuleAttributeLevel, RuleOperator, RuleType
from eligibility_signposting_api.repos import EligibilityRepo, NotFoundError, RulesRepo
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from tests.utils.builders import CampaignConfigFactory, IterationFactory, IterationRuleFactory
from tests.utils.matchers.eligibility import is_condition, is_eligibility_status


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
    assert_that(actual, is_eligibility_status().with_conditions(empty()))


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
                "ATTRIBUTE_TYPE": "PERSON",
                "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
                "POSTCODE": postcode,
            },
            {"NHS_NUMBER": f"PERSON#{nhs_number}", "ATTRIBUTE_TYPE": "COHORT", "COHORT_MAP": {}},
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
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.actionable))
        ),
    )


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
                "ATTRIBUTE_TYPE": "PERSON",
                "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
                "POSTCODE": postcode,
            },
            {"NHS_NUMBER": f"PERSON#{nhs_number}", "ATTRIBUTE_TYPE": "COHORT", "COHORT_MAP": {}},
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
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_actionable))
        ),
    )
