import datetime
import json
from typing import Any

import pytest
from faker import Faker
from freezegun import freeze_time
from hamcrest import assert_that, contains_exactly, contains_inanyorder, equal_to, has_item, has_items

from eligibility_signposting_api.model import rules
from eligibility_signposting_api.model import rules as rules_model
from eligibility_signposting_api.model.eligibility import (
    ConditionName,
    DateOfBirth,
    NHSNumber,
    Postcode,
    RuleResult,
    Status,
)
from eligibility_signposting_api.services.calculators.eligibility_calculator import EligibilityCalculator
from tests.fixtures.builders.model import rule as rule_builder
from tests.fixtures.builders.repos.person import person_rows_builder
from tests.fixtures.matchers.eligibility import (
    is_cohort_result,
    is_condition,
    is_eligibility_status,
    is_reason,
)
from tests.fixtures.matchers.rules import is_iteration_rule


class TestEligibilityCalculator:

    @staticmethod
    def test_get_redirect_rules(faker: Faker):
        #Given
        campaign_configs = [
            (
                rule_builder.CampaignConfigFactory.build(
                    target="RSV",
                    iterations=[
                        rule_builder.IterationFactory.build(
                            iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort2")],
                            default_comms_routing= "defaultcomms",
                            actions_mapper = {"A key": {"anotherkey": "anothervalue"}},
                            iteration_rules=[rule_builder.ICBRedirectRuleFactory.build()]
                        )
                    ],
                )
            )
        ]
        iteration = campaign_configs[0].iterations[0]

        #when
        actual_rules, actual_action_mapper, actual_default_comms = EligibilityCalculator.get_redirect_rules(iteration)

        #then
        assert_that(
            actual_rules,
            has_item(is_iteration_rule().with_name(campaign_configs[0].iterations[0].iteration_rules[0].name))
        )
        assert actual_action_mapper == campaign_configs[0].iterations[0].actions_mapper
        assert actual_default_comms == campaign_configs[0].iterations[0].default_comms_routing


def test_not_base_eligible(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"])
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort2")]
                    )
                ],
            )
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_eligible))
        ),
    )


@pytest.mark.parametrize(
    ("person_cohorts", "iteration_cohorts", "status", "test_comment"),
    [
        (["cohort1"], ["elid_all_people"], Status.actionable, "Only magic cohort present"),
        (["cohort1"], ["elid_all_people", "cohort1"], Status.actionable, "Magic cohort with other cohorts"),
        (["cohort1"], ["cohort2"], Status.not_eligible, "No magic cohort. No matching person cohort"),
        ([], ["elid_all_people"], Status.actionable, "No person cohorts. Only magic cohort present"),
    ],
)
def test_base_eligible_with_when_magic_cohort_is_present(
    faker: Faker, person_cohorts: list[str], iteration_cohorts: list[str], status: Status, test_comment: str
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=79))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=person_cohorts)
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(cohort_label=label) for label in iteration_cohorts
                    ],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(status))
        ),
        test_comment,
    )


@freeze_time("2025-04-25")
def test_only_live_campaigns_considered(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"])
    campaign_configs = [
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

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_eligible))
        ),
    )


def test_base_eligible_and_simple_rule_includes(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=79))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [
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

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.actionable))
        ),
    )


def test_base_eligible_but_simple_rule_excludes(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [
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

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

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
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [
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

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_actionable))
        ),
    )


@pytest.mark.parametrize(
    ("rule_type", "expected_status"),
    [
        (rules_model.RuleType.suppression, Status.not_actionable),
        (rules_model.RuleType.filter, Status.not_eligible),
        (rules_model.RuleType.redirect, Status.actionable),
    ],
)
def test_rule_types_cause_correct_statuses(rule_type: rules_model.RuleType, expected_status: Status, faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [
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

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
    )


def test_multiple_rule_types_cause_correct_status(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=18, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            priority=rules_model.RulePriority(5), type=rules_model.RuleType.suppression
                        ),
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            priority=rules_model.RulePriority(10), type=rules_model.RuleType.filter
                        ),
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            priority=rules_model.RulePriority(15), type=rules_model.RuleType.suppression
                        ),
                    ],
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

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
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=rules_model.RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=rules_model.RulePriority(5)),
            Status.not_actionable,
        ),
        (
            "two rules, rule 1 excludes, same priority, should allow",
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=rules_model.RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(
                priority=rules_model.RulePriority(5), comparator=rules_model.RuleComparator("NW1")
            ),
            Status.actionable,
        ),
        (
            "two rules, rule 2 excludes, same priority, should allow",
            rule_builder.PersonAgeSuppressionRuleFactory.build(
                priority=rules_model.RulePriority(5), comparator=rules_model.RuleComparator("-65")
            ),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=rules_model.RulePriority(5)),
            Status.actionable,
        ),
        (
            "two rules, rule 1 excludes, different priority, should exclude",
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=rules_model.RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(
                priority=rules_model.RulePriority(10), comparator=rules_model.RuleComparator("NW1")
            ),
            Status.not_actionable,
        ),
        (
            "two rules, rule 2 excludes, different priority, should exclude",
            rule_builder.PersonAgeSuppressionRuleFactory.build(
                priority=rules_model.RulePriority(5), comparator=rules_model.RuleComparator("-65")
            ),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=rules_model.RulePriority(10)),
            Status.not_actionable,
        ),
        (
            "two rules, both excludes, different priority, should exclude",
            rule_builder.PersonAgeSuppressionRuleFactory.build(priority=rules_model.RulePriority(5)),
            rule_builder.PostcodeSuppressionRuleFactory.build(priority=rules_model.RulePriority(10)),
            Status.not_actionable,
        ),
    ],
)
def test_rules_with_same_priority_must_all_match_to_exclude(
    test_comment: str,
    rule1: rules_model.IterationRule,
    rule2: rules_model.IterationRule,
    expected_status: Status,
    faker: Faker,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(
        nhs_number, date_of_birth=date_of_birth, postcode=Postcode("SW19 2BH"), cohorts=["cohort1"]
    )
    campaign_configs = [
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

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
        test_comment,
    )


def test_multiple_conditions_where_both_are_actionable(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=78))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                )
            ],
        ),
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.actionable),
                is_condition().with_condition_name(ConditionName("COVID")).and_status(Status.actionable),
            )
        ),
    )


def test_multiple_conditions_where_all_give_unique_statuses(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=78))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(comparator="-85")],
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="FLU",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort2")],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(comparator="-85")],
                )
            ],
        ),
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.actionable),
                is_condition().with_condition_name(ConditionName("COVID")).and_status(Status.not_actionable),
                is_condition().with_condition_name(ConditionName("FLU")).and_status(Status.not_eligible),
            )
        ),
    )


@pytest.mark.parametrize(
    ("test_comment", "campaign1", "campaign2"),
    [
        (
            "1st campaign allows, 2nd excludes",
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                    )
                ],
            ),
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(comparator="-85")],
                    )
                ],
            ),
        ),
        (
            "1st campaign excludes, 2nd allows",
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(comparator="-85")],
                    )
                ],
            ),
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                    )
                ],
            ),
        ),
    ],
)
def test_multiple_campaigns_for_single_condition(
    test_comment: str, campaign1: rules_model.CampaignConfig, campaign2: rules_model.CampaignConfig, faker: Faker
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=78))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])
    campaign_configs = [campaign1, campaign2]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            contains_exactly(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.actionable))
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("icb", "rule_type", "expected_status"),
    [
        ("QE1", rules_model.RuleType.suppression, Status.actionable),
        ("QWU", rules_model.RuleType.suppression, Status.not_actionable),
        ("", rules_model.RuleType.suppression, Status.not_actionable),
        (None, rules_model.RuleType.suppression, Status.not_actionable),
        ("QE1", rules_model.RuleType.filter, Status.actionable),
        ("QWU", rules_model.RuleType.filter, Status.not_eligible),
        ("", rules_model.RuleType.filter, Status.not_eligible),
        (None, rules_model.RuleType.filter, Status.not_eligible),
    ],
)
def test_base_eligible_and_icb_example(
    icb: str | None, rule_type: rules_model.RuleType, expected_status: Status, faker: Faker
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb=icb)
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_rules=[rule_builder.ICBSuppressionRuleFactory.build(type=rule_type)],
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
    )


@pytest.mark.parametrize(
    ("vaccine", "last_successful_date", "expected_status", "test_comment"),
    [
        ("RSV", "20240601", Status.not_actionable, "last_successful_date is a past date"),
        ("RSV", "20250101", Status.not_actionable, "last_successful_date is today"),
        # Below is a non-ideal situation (might be due to a data entry error), so considered as actionable.
        ("RSV", "20260101", Status.actionable, "last_successful_date is a future date"),
        ("RSV", "20230601", Status.actionable, "last_successful_date is a long past"),
        ("RSV", "", Status.actionable, "last_successful_date is empty"),
        ("RSV", None, Status.actionable, "last_successful_date is none"),
        ("COVID", "20240601", Status.actionable, "No RSV row"),
    ],
)
@freeze_time("2025-01-01")
def test_status_on_target_based_on_last_successful_date(
    vaccine: str, last_successful_date: str, expected_status: Status, test_comment: str, faker: Faker
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    target_rows = person_rows_builder(
        nhs_number,
        cohorts=["cohort1"],
        vaccines=[
            (
                vaccine,
                datetime.datetime.strptime(last_successful_date, "%Y%m%d").replace(tzinfo=datetime.UTC)
                if last_successful_date
                else None,
            )
        ],
    )

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_rules=[
                        rule_builder.IterationRuleFactory.build(
                            type=rules.RuleType.suppression,
                            name=rules.RuleName("You have already been vaccinated against RSV in the last year"),
                            description=rules.RuleDescription(
                                "Exclude anyone Completed RSV Vaccination in the last year"
                            ),
                            priority=10,
                            operator=rules.RuleOperator.day_gte,
                            attribute_level=rules.RuleAttributeLevel.TARGET,
                            attribute_name=rules.RuleAttributeName("LAST_SUCCESSFUL_DATE"),
                            comparator=rules.RuleComparator("-365"),
                            attribute_target=rules.RuleAttributeTarget("RSV"),
                        ),
                        rule_builder.IterationRuleFactory.build(
                            type=rules.RuleType.suppression,
                            name=rules.RuleName("You have a vaccination date in the future for RSV"),
                            description=rules.RuleDescription("Exclude anyone with future Completed RSV Vaccination"),
                            priority=10,
                            operator=rules.RuleOperator.day_lte,
                            attribute_level=rules.RuleAttributeLevel.TARGET,
                            attribute_name=rules.RuleAttributeName("LAST_SUCCESSFUL_DATE"),
                            comparator=rules.RuleComparator("0"),
                            attribute_target=rules.RuleAttributeTarget("RSV"),
                        ),
                    ],
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(target_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("attribute_name", "expected_status", "test_comment"),
    [
        (
            rules.RuleAttributeName("COHORT_LABEL"),
            Status.not_eligible,
            "cohort label provided",
        ),
        (
            None,
            Status.not_eligible,
            "cohort label is the default attribute name for the cohort attribute level",
        ),
        (
            rules.RuleAttributeName("LOCATION"),
            Status.actionable,
            "attribute name that is not cohort label",
        ),
    ],
)
def test_status_on_cohort_attribute_level(
    attribute_name: rules.RuleAttributeName, expected_status: Status, test_comment: str, faker: Faker
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_row: list[dict[str, Any]] = person_rows_builder(
        nhs_number, cohorts=["cohort1", "covid_eligibility_complaint_list"]
    )
    person_row_with_extra_items_in_cohort_row = [
        {**r, "LOCATION": "HP1"} for r in person_row if r.get("ATTRIBUTE_TYPE", "") == "COHORTS"
    ]

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[
                        rule_builder.IterationRuleFactory.build(
                            type=rules.RuleType.filter,
                            name=rules.RuleName("Exclude those in a complaint cohort"),
                            description=rules.RuleDescription(
                                "Ensure anyone who has registered a complaint is not shown as eligible"
                            ),
                            priority=15,
                            operator=rules.RuleOperator.member_of,
                            attribute_level=rules.RuleAttributeLevel.COHORT,
                            attribute_name=attribute_name,
                            comparator=rules.RuleComparator("covid_eligibility_complaint_list"),
                        )
                    ],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_row_with_extra_items_in_cohort_row, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("person_cohorts", "expected_status", "test_comment"),
    [
        (["cohort1", "cohort2"], Status.actionable, "cohort1 is not actionable, cohort 2 is actionable"),
        (["cohort3", "cohort2"], Status.actionable, "cohort3 is not eligible, cohort 2 is actionable"),
        (["cohort1"], Status.not_actionable, "cohort1 is not actionable"),
    ],
)
def test_status_if_iteration_rules_contains_cohort_label_field(
    person_cohorts, expected_status: Status, test_comment: str, faker: Faker
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=person_cohorts)
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(cohort_label="cohort1"),
                        rule_builder.IterationCohortFactory.build(cohort_label="cohort2"),
                    ],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build(cohort_label="cohort1")],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("rule_stop", "expected_reason_results", "test_comment"),  # Changed expected_reasons to expected_reason_results
    [
        (
            rules.RuleStop(True),  # noqa: FBT003
            [
                RuleResult("reason 1"),
                RuleResult("reason 2"),
            ],
            "rule_stop is True, last rule should not run",
        ),
        (
            rules.RuleStop(False),  # noqa: FBT003
            [
                RuleResult("reason 1"),
                RuleResult("reason 2"),
                RuleResult("reason 3"),
            ],
            "rule_stop is False, last rule should run",
        ),
    ],
)
def test_rules_stop_behavior(
    rule_stop: rules.RuleStop, expected_reason_results: list[RuleResult], test_comment: str, faker: Faker
) -> None:
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))
    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])

    # Build campaign configuration
    campaign_config = rule_builder.CampaignConfigFactory.build(
        target="RSV",
        iterations=[
            rule_builder.IterationFactory.build(
                iteration_rules=[
                    rule_builder.PersonAgeSuppressionRuleFactory.build(
                        priority=10, description="reason 1", rule_stop=rule_stop
                    ),
                    rule_builder.PersonAgeSuppressionRuleFactory.build(priority=10, description="reason 2"),
                    rule_builder.PersonAgeSuppressionRuleFactory.build(priority=15, description="reason 3"),
                ],
                iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
            )
        ],
    )

    calculator = EligibilityCalculator(person_rows, [campaign_config])

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.not_actionable))
                .and_cohort_results(
                    has_items(
                        is_cohort_result().with_reasons(
                            contains_inanyorder(
                                *[is_reason().with_rule_result(equal_to(result)) for result in expected_reason_results]
                            )
                        )
                    )
                )
            )
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("person_cohorts", "iteration_cohorts", "expected_status", "expected_cohorts"),
    [
        (
            ["covid_cohort", "flu_cohort"],
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            Status.not_eligible,
            ["rsv_clinical_cohort", "rsv_75_rolling"],
        ),
        (
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            Status.actionable,
            ["rsv_clinical_cohort"],
        ),
        (
            ["covid_cohort", "rsv_75_rolling"],
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            Status.not_actionable,
            ["rsv_75_rolling"],
        ),
        (
            ["covid_cohort", "rsv_clinical_cohort"],
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            Status.actionable,
            ["rsv_clinical_cohort"],
        ),
        (
            ["rsv_75to79_2024", "rsv_75_rolling"],
            ["rsv_75to79_2024", "rsv_75_rolling"],
            Status.not_actionable,
            ["rsv_75_rolling", "rsv_75to79_2024"],
        ),
    ],
)
def test_eligibility_results_when_multiple_cohorts(
    person_cohorts: list[str],
    iteration_cohorts: list[str],
    expected_status: Status,
    expected_cohorts: list[str],
    faker: Faker,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    dob_person_less_than_75 = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=dob_person_less_than_75, cohorts=person_cohorts)
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(cohort_group=None, cohort_label=cohorts)
                        for cohorts in iteration_cohorts
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(cohort_label="rsv_75_rolling"),
                        rule_builder.PersonAgeSuppressionRuleFactory.build(cohort_label="rsv_75to79_2024"),
                    ],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(expected_status))
                .and_cohort_results(
                    contains_inanyorder(
                        *[
                            is_cohort_result().with_cohort_code(equal_to(cohort_label))
                            for cohort_label in expected_cohorts
                        ]
                    )
                )
            )
        ),
    )

def test_correct_actions_determined_from_redirect_r_rules(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    dob_person_less_than_75 = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=dob_person_less_than_75, cohorts="cohort1")
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort2")],
                        default_comms_routing="defaultcomms",
                        actions_mapper={"A key": {"ActionCode": "ActionCode1",
                                                  "ActionDescription": "Action description",
                                                  "ActionType": "ActionType",
                                                  "ActionLink": "ActionLink",
                                                  }},
                        iteration_rules=[rule_builder.ICBRedirectRuleFactory.build()]
                    )
                ],
            )
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    pass

def test_cohort_label_not_supported_used_in_r_rules(faker: Faker):
    pass
