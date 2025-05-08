import datetime
from unittest.mock import MagicMock

import pytest
from faker import Faker
from freezegun import freeze_time
from hamcrest import assert_that, empty, has_item

from eligibility_signposting_api.model.eligibility import ConditionName, DateOfBirth, NHSNumber, Status
from eligibility_signposting_api.model.rules import RuleAttributeLevel, RuleOperator, RuleType
from eligibility_signposting_api.repos import EligibilityRepo, NotFoundError, RulesRepo
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from tests.fixtures.builders.model.rule import (
    CampaignConfigFactory,
    IterationCohortFactory,
    IterationFactory,
    IterationRuleFactory,
)
from tests.fixtures.matchers.eligibility import is_condition, is_eligibility_status


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


def test_not_base_eligible(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=[
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "PERSON",
            },
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "COHORTS",
                "COHORT_MAP": {"cohorts": {"M": {"cohort1": {"dateJoined": {"S": faker.past_date()}}}}},
            },
        ]
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    IterationFactory.build(
                        iteration_cohorts=[IterationCohortFactory.build(cohort_label="cohort2")],
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
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_eligible))
        ),
    )


@freeze_time("2025-04-25")
def test_only_live_campaigns_considered(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=[
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "PERSON",
            },
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "COHORTS",
                "COHORT_MAP": {"cohorts": {"M": {"cohort1": {"dateJoined": {"S": faker.past_date()}}}}},
            },
        ]
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            CampaignConfigFactory.build(
                name="Live",
                target="RSV",
                iterations=[
                    IterationFactory.build(
                        iteration_cohorts=[IterationCohortFactory.build(cohort_label="cohort2")],
                    )
                ],
                start_date=datetime.date(2025, 4, 20),
                end_date=datetime.date(2025, 4, 30),
            ),
            CampaignConfigFactory.build(
                name="No longer live",
                target="RSV",
                iterations=[
                    IterationFactory.build(
                        iteration_cohorts=[
                            IterationCohortFactory.build(cohort_label="cohort1"),
                            IterationCohortFactory.build(cohort_label="cohort2"),
                        ],
                    )
                ],
                start_date=datetime.date(2025, 4, 1),
                end_date=datetime.date(2025, 4, 24),
            ),
        ]
    )

    ps = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = ps.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_eligible))
        ),
    )


def test_base_eligible_and_simple_rule_includes(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=79))

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=[
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "PERSON",
                "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
            },
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "COHORTS",
                "COHORT_MAP": {"cohorts": {"M": {"cohort1": {"dateJoined": {"S": faker.past_date()}}}}},
            },
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
                        ],
                        iteration_cohorts=[IterationCohortFactory.build(cohort_label="cohort1")],
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


def test_base_eligible_but_simple_rule_excludes(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(maximum_age=74))

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=[
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "PERSON",
                "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
            },
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "COHORTS",
                "COHORT_MAP": {"cohorts": {"M": {"cohort1": {"dateJoined": {"S": faker.past_date()}}}}},
            },
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
                                type=RuleType.suppression,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.year_gt,
                                comparator="-75",
                            ),
                            IterationRuleFactory.build(
                                type=RuleType.suppression,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.lt,
                                comparator="19440902",
                            ),
                        ],
                        iteration_cohorts=[IterationCohortFactory.build(cohort_label="cohort1")],
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


@freeze_time("2025-04-25")
def test_simple_rule_only_excludes_from_live_iteration(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=[
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "PERSON",
                "DATE_OF_BIRTH": date_of_birth.strftime("%Y%m%d"),
            },
            {
                "NHS_NUMBER": f"PERSON#{nhs_number}",
                "ATTRIBUTE_TYPE": "COHORTS",
                "COHORT_MAP": {"cohorts": {"M": {"cohort1": {"dateJoined": {"S": faker.past_date()}}}}},
            },
        ]
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    IterationFactory.build(
                        name="old iteration - would not exclude 74 year old",
                        iteration_rules=[
                            IterationRuleFactory.build(
                                type=RuleType.suppression,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.year_gt,
                                comparator="-65",
                            ),
                        ],
                        iteration_cohorts=[IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_date=datetime.date(2025, 4, 10),
                    ),
                    IterationFactory.build(
                        name="current - would exclude 74 year old",
                        iteration_rules=[
                            IterationRuleFactory.build(
                                type=RuleType.suppression,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.year_gt,
                                comparator="-75",
                            ),
                        ],
                        iteration_cohorts=[IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_date=datetime.date(2025, 4, 20),
                    ),
                    IterationFactory.build(
                        name="next iteration - would not exclude 74 year old",
                        iteration_rules=[
                            IterationRuleFactory.build(
                                type=RuleType.filter,
                                attribute_level=RuleAttributeLevel.PERSON,
                                attribute_name="DATE_OF_BIRTH",
                                operator=RuleOperator.year_gt,
                                comparator="-65",
                            ),
                        ],
                        iteration_cohorts=[IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_date=datetime.date(2025, 4, 30),
                    ),
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
