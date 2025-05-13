import datetime
from unittest.mock import MagicMock

import pytest
from faker import Faker
from freezegun import freeze_time
from hamcrest import assert_that, empty, has_item

from eligibility_signposting_api.model.eligibility import ConditionName, DateOfBirth, NHSNumber, Postcode, Status
from eligibility_signposting_api.model.rules import IterationDate, IterationRule, RuleComparator, RulePriority, RuleType
from eligibility_signposting_api.repos import EligibilityRepo, NotFoundError, RulesRepo
from eligibility_signposting_api.services import EligibilityService, UnknownPersonError
from tests.fixtures.builders.model import rule as rule_builder
from tests.fixtures.builders.repos.eligibility import eligibility_rows_builder
from tests.fixtures.matchers.eligibility import is_condition, is_eligibility_status


@pytest.fixture(scope="session")
def faker() -> Faker:
    return Faker("en_UK")


def test_eligibility_service_returns_from_repo():
    # Given
    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility = MagicMock(return_value=[])
    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber("1234567890"))

    # Then
    assert_that(actual, is_eligibility_status().with_conditions(empty()))


def test_eligibility_service_for_nonexistent_nhs_number():
    # Given
    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(side_effect=NotFoundError)
    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    with pytest.raises(UnknownPersonError):
        service.get_eligibility_status(NHSNumber("1234567890"))


def test_not_base_eligible(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)

    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=eligibility_rows_builder(nhs_number, cohorts=["cohort1"])
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort2")]
                    )
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

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
        return_value=eligibility_rows_builder(nhs_number, cohorts=["cohort1"])
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                name="Live",
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort2")],
                    )
                ],
                start_date=datetime.date(2025, 4, 20),
                end_date=datetime.date(2025, 4, 30),
            ),
            rule_builder.CampaignConfigFactory.build(
                name="No longer live",
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[
                            rule_builder.IterationCohortFactory.build(cohort_label="cohort1"),
                            rule_builder.IterationCohortFactory.build(cohort_label="cohort2"),
                        ],
                    )
                ],
                start_date=datetime.date(2025, 4, 1),
                end_date=datetime.date(2025, 4, 24),
            ),
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

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
        return_value=eligibility_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    )
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

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
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=74))

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=eligibility_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    )
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

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
        return_value=eligibility_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        name="old iteration - would not exclude 74 year old",
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(comparator="-65")],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_date=datetime.date(2025, 4, 10),
                    ),
                    rule_builder.IterationFactory.build(
                        name="current - would exclude 74 year old",
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_date=datetime.date(2025, 4, 20),
                    ),
                    rule_builder.IterationFactory.build(
                        name="next iteration - would not exclude 74 year old",
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(comparator="-65")],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_date=datetime.date(2025, 4, 30),
                    ),
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_actionable))
        ),
    )


@freeze_time("2025-04-25")
def test_campaign_with_no_active_iteration_not_considered(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(return_value=eligibility_rows_builder(nhs_number))
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_date=IterationDate(datetime.date(2025, 4, 26)),
                    )
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(actual, is_eligibility_status().with_conditions(empty()))


@pytest.mark.parametrize(
    ("rule_type", "expected_status"),
    [
        (RuleType.suppression, Status.not_actionable),
        (RuleType.filter, Status.not_eligible),
        (RuleType.redirect, Status.actionable),
    ],
)
def test_rule_types_cause_correct_statuses(rule_type: RuleType, expected_status: Status, faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=74))

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=eligibility_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(type=rule_type)],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    )
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
    )


def test_multiple_rule_types_cause_correct_status(faker: Faker):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=74))

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=eligibility_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_rules=[
                            rule_builder.PersonAgeSuppressionRuleFactory.build(
                                priority=RulePriority(5), type=RuleType.suppression
                            ),
                            rule_builder.PersonAgeSuppressionRuleFactory.build(
                                priority=RulePriority(10), type=RuleType.filter
                            ),
                            rule_builder.PersonAgeSuppressionRuleFactory.build(
                                priority=RulePriority(15), type=RuleType.suppression
                            ),
                        ],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    )
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_eligible))
        ),
    )


@pytest.mark.parametrize(
    ("test_comment", "rule1", "rule2", "expected_status"),
    [
        (
            "two rules, both exclude, same priority, should exclude",
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=RulePriority(5)),
            Status.not_actionable,
        ),
        (
            "two rules, rule 1 excludes, same priority, should allow",
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(
                priority=RulePriority(5), comparator=RuleComparator("NW1")
            ),
            Status.actionable,
        ),
        (
            "two rules, rule 2 excludes, same priority, should allow",
            rule_builder.PersonAgeSuppressionRuleFactory.build(
                priority=RulePriority(5), comparator=RuleComparator("-65")
            ),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=RulePriority(5)),
            Status.actionable,
        ),
        (
            "two rules, rule 1 excludes, different priority, should exclude",
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(
                priority=RulePriority(10), comparator=RuleComparator("NW1")
            ),
            Status.not_actionable,
        ),
        (
            "two rules, rule 2 excludes, different priority, should exclude",
            rule_builder.PersonAgeSuppressionRuleFactory.build(
                priority=RulePriority(5), comparator=RuleComparator("-65")
            ),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=RulePriority(10)),
            Status.not_actionable,
        ),
        (
            "two rules, both excludes, different priority, should exclude",
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=RulePriority(10)),
            Status.not_actionable,
        ),
    ],
)
def test_rules_with_same_priority_must_all_match_to_exclude(
    test_comment: str, rule1: IterationRule, rule2: IterationRule, expected_status: Status, faker: Faker
):
    # Given
    nhs_number = NHSNumber(f"5{faker.random_int(max=999999999):09d}")
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    eligibility_repo = MagicMock(spec=EligibilityRepo)
    rules_repo = MagicMock(spec=RulesRepo)
    eligibility_repo.get_eligibility_data = MagicMock(
        return_value=eligibility_rows_builder(
            nhs_number, date_of_birth=date_of_birth, postcode=Postcode("SW19 2BH"), cohorts=["cohort1"]
        )
    )
    rules_repo.get_campaign_configs = MagicMock(
        return_value=[
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_rules=[rule1, rule2],
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    )
                ],
            )
        ]
    )

    service = EligibilityService(eligibility_repo, rules_repo)

    # When
    actual = service.get_eligibility_status(NHSNumber(nhs_number))

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
        test_comment,
    )
