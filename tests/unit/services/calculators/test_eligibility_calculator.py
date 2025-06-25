import datetime
from typing import Any

import pytest
from faker import Faker
from freezegun import freeze_time
from hamcrest import assert_that, contains_exactly, contains_inanyorder, equal_to, has_item, has_items, is_in
from pydantic import ValidationError

from eligibility_signposting_api.model import rules
from eligibility_signposting_api.model import rules as rules_model
from eligibility_signposting_api.model.eligibility import (
    ActionCode,
    ActionDescription,
    ActionType,
    ConditionName,
    DateOfBirth,
    NHSNumber,
    Postcode,
    RuleDescription,
    Status,
    SuggestedAction,
    SuggestedActions,
    UrlLabel,
    UrlLink,
)
from eligibility_signposting_api.model.rules import ActionsMapper, AvailableAction
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
    def test_get_redirect_rules():
        # Given

        iteration = rule_builder.IterationFactory.build(
            iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort2")],
            default_comms_routing="defaultcomms",
            actions_mapper=rule_builder.ActionsMapperFactory.build(
                root={
                    "ActionCode1": AvailableAction(
                        ActionType="ActionType1",
                        ExternalRoutingCode="ActionCode1",
                        ActionDescription="ActionDescription1",
                        UrlLink="ActionUrl1",
                        UrlLabel="ActionLabel1",
                    ),
                    "defaultcomms": AvailableAction(
                        ActionType="ActionType2",
                        ExternalRoutingCode="defaultcomms",
                        ActionDescription="ActionDescription2",
                        UrlLink="ActionUrl2",
                        UrlLabel="ActionLabel2",
                    ),
                }
            ),
            iteration_rules=[rule_builder.ICBRedirectRuleFactory.build()],
        )

        # when
        actual_rules, actual_action_mapper, actual_default_comms = EligibilityCalculator.get_redirect_rules(iteration)

        # then
        assert_that(actual_rules, has_item(is_iteration_rule().with_name(iteration.iteration_rules[0].name)))
        assert actual_action_mapper == iteration.actions_mapper
        assert actual_default_comms == iteration.default_comms_routing


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


@pytest.mark.parametrize(
    "iteration_type",
    ["A", "M", "S", "O"],
)
def test_campaigns_with_applicable_iteration_types_in_campaign_level_considered(iteration_type: str, faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number)
    campaign_configs = [rule_builder.CampaignConfigFactory.build(target="RSV", iteration_type=iteration_type)]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(is_in([Status.actionable, Status.not_actionable, Status.not_eligible]))
            ),
        ),
    )


@pytest.mark.parametrize(
    "iteration_type",
    ["A", "M", "S", "O"],
)
def test_campaigns_with_applicable_iteration_types_in_iteration_level_considered(iteration_type: str, faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number)
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV", iterations=[rule_builder.IterationFactory.build(type=iteration_type)]
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(is_in([Status.actionable, Status.not_actionable, Status.not_eligible]))
            ),
        ),
    )


@pytest.mark.parametrize(
    "iteration_type",
    ["NA", "N", "FAKE", "F"],
)
def test_invalid_iteration_types_in_campaign_level_raises_validation_error(iteration_type: str):
    with pytest.raises(ValidationError):
        rule_builder.CampaignConfigFactory.build(target="RSV", iteration_type=iteration_type)


@pytest.mark.parametrize(
    "iteration_type",
    ["NA", "N", "FAKE", "F"],
)
def test_invalid_iteration_types_in_iteration_level_raises_validation_error(iteration_type: str):
    with pytest.raises(ValidationError):
        rule_builder.CampaignConfigFactory.build(
            target="RSV", iterations=[rule_builder.IterationFactory.build(type=iteration_type)]
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
    [(rules_model.RuleType.suppression, Status.not_actionable), (rules_model.RuleType.filter, Status.not_eligible)],
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
            has_item(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(expected_status)
                .and_actions(SuggestedActions([]))
            )
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

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"], icb="QE1")
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                    default_comms_routing="defaultcomms",
                    actions_mapper=rule_builder.ActionsMapperFactory.build(
                        root={"rule_1_comms_routing": book_nbs_comms, "defaultcomms": default_comms_detail}
                    ),
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(),
                        rule_builder.ICBRedirectRuleFactory.build(),
                    ],
                    default_comms_routing="defaultcomms",
                    actions_mapper=rule_builder.ActionsMapperFactory.build(
                        root={"ActionCode1": book_nbs_comms, "defaultcomms": default_comms_detail}
                    ),
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
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(Status.actionable)
                .and_actions(SuggestedActions([suggested_action_for_default_comms])),
                is_condition()
                .with_condition_name(ConditionName("COVID"))
                .and_status(Status.actionable)
                .and_actions(SuggestedActions([suggested_action_for_book_nbs])),
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
    actual = calculator.evaluate_eligibility(include_actions_flag=False)

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(Status.actionable)
                .and_actions(None),
                is_condition()
                .with_condition_name(ConditionName("COVID"))
                .and_status(Status.not_actionable)
                .and_actions(None),
                is_condition()
                .with_condition_name(ConditionName("FLU"))
                .and_status(Status.not_eligible)
                .and_actions(None),
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
                    iteration_rules=[rule_builder.ICBFilterRuleFactory.build(type=rule_type)],
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
                RuleDescription("reason 1"),
                RuleDescription("reason 2"),
            ],
            "rule_stop is True, last rule should not run",
        ),
        (
            rules.RuleStop(False),  # noqa: FBT003
            [
                RuleDescription("reason 1"),
                RuleDescription("reason 2"),
                RuleDescription("reason 3"),
            ],
            "rule_stop is False, last rule should run",
        ),
    ],
)
def test_rules_stop_behavior(
    rule_stop: rules.RuleStop, expected_reason_results: list[RuleDescription], test_comment: str, faker: Faker
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
                iteration_cohorts=[
                    rule_builder.IterationCohortFactory.build(cohort_group="cohort_group1", cohort_label="cohort1")
                ],
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
                                *[
                                    is_reason().with_rule_description(equal_to(result))
                                    for result in expected_reason_results
                                ]
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
            ["rsv_clinical_cohort_group", "rsv_75_rolling_group"],
        ),
        (
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            Status.actionable,
            ["rsv_clinical_cohort_group"],
        ),
        (
            ["covid_cohort", "rsv_75_rolling"],
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            Status.not_actionable,
            ["rsv_75_rolling_group"],
        ),
        (
            ["covid_cohort", "rsv_clinical_cohort"],
            ["rsv_clinical_cohort", "rsv_75_rolling"],
            Status.actionable,
            ["rsv_clinical_cohort_group"],
        ),
        (
            ["rsv_75to79_2024", "rsv_75_rolling"],
            ["rsv_75to79_2024", "rsv_75_rolling"],
            Status.not_actionable,
            ["rsv_75_rolling_group", "rsv_75to79_2024_group"],
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
                        rule_builder.IterationCohortFactory.build(
                            cohort_group=f"{cohorts}_group",
                            cohort_label=cohorts,
                            positive_description="positive description",
                            negative_description="negative description",
                        )
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


@pytest.mark.parametrize(
    ("person_rows", "expected_status", "expected_cohort_group_and_description", "test_comment"),
    [
        (
            person_rows_builder(nhs_number="123", cohorts=[], postcode="AC01", de=True, icb="QE1"),
            Status.not_eligible,
            [
                ("magic cohort group", "magic negative description"),
                ("rsv_age_range", "rsv_age_range negative description"),
            ],
            "rsv_75_rolling is not base-eligible & magic cohort group not eligible by F rules ",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="AC01", de=True, icb="QE1"),
            Status.not_eligible,
            [
                ("magic cohort group", "magic negative description"),
                ("rsv_age_range", "rsv_age_range negative description"),
            ],
            "all the cohorts are not-eligible by F rules",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="SW19", de=False, icb="QE1"),
            Status.not_actionable,
            [
                ("magic cohort group", "magic positive description"),
                ("rsv_age_range", "rsv_age_range positive description"),
            ],
            "all the cohorts are not-actionable",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="AC01", de=False, icb="QE1"),
            Status.actionable,
            [
                ("magic cohort group", "magic positive description"),
                ("rsv_age_range", "rsv_age_range positive description"),
            ],
            "all the cohorts are actionable",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="AC01", de=False, icb="NOT_QE1"),
            Status.actionable,
            [("magic cohort group", "magic positive description")],
            "magic_cohort is actionable, but not others",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="SW19", de=False, icb="NOT_QE1"),
            Status.not_actionable,
            [("magic cohort group", "magic positive description")],
            "magic_cohort is not-actionable, but others are not eligible",
        ),
    ],
)
def test_cohort_groups_and_their_descriptions_when_magic_cohort_is_present(
    person_rows: list[dict[str, Any]],
    expected_status: str,
    expected_cohort_group_and_description: list[tuple[str, str]],
    test_comment: str,
):
    # Given
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.Rsv75RollingCohortFactory.build(),
                        rule_builder.MagicCohortFactory.build(),
                    ],
                    iteration_rules=[
                        # F common rule
                        rule_builder.DetainedEstateSuppressionRuleFactory.build(type=rules.RuleType.filter),
                        # F rules for rsv_75_rolling
                        rule_builder.ICBFilterRuleFactory.build(
                            type=rules.RuleType.filter, cohort_label=rules.CohortLabel("rsv_75_rolling")
                        ),
                        # S common rule
                        rule_builder.PostcodeSuppressionRuleFactory.build(
                            comparator=rules.RuleComparator("SW19"),
                        ),
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
                .and_cohort_results(
                    contains_exactly(
                        *[
                            is_cohort_result()
                            .with_cohort_code(item[0])
                            .with_description(item[1])
                            .with_status(expected_status)
                            for item in expected_cohort_group_and_description
                        ]
                    )
                )
            )
        ),
        test_comment,
    )


def test_cohort_groups_and_their_descriptions_when_best_status_is_not_eligible(
    faker: Faker,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=[])
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.Rsv75RollingCohortFactory.build(),
                        rule_builder.Rsv75to79CohortFactory.build(),
                        rule_builder.RsvPretendClinicalCohortFactory.build(),
                    ],
                    iteration_rules=[rule_builder.PostcodeSuppressionRuleFactory.build()],
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
                .and_status(Status.not_eligible)
                .and_cohort_results(
                    contains_exactly(
                        is_cohort_result()
                        .with_cohort_code("rsv_age_range")
                        .with_description("rsv_age_range negative description"),
                        is_cohort_result()
                        .with_cohort_code("rsv_clinical_cohort")
                        .with_description("rsv_clinical_cohort negative description"),
                    )
                )
            )
        ),
    )


@pytest.mark.parametrize(
    ("person_cohorts", "expected_cohort_group_and_description_and_s_rule_names", "test_comment"),
    [
        (
            ["rsv_75_rolling"],
            [("rsv_age_range", "rsv_age_range positive description", ["Excluded postcode In SW19"])],
            "rsv_75_rolling is not-actionable, others are not-eligible",
        ),
        (
            ["rsv_75_rolling", "rsv_75to79_2024"],
            [
                (
                    "rsv_age_range",
                    "rsv_age_range positive description",
                    ["Excluded postcode In SW19", "Excluded postcode In SW19"],
                )
            ],
            "rsv_75_rolling, rsv_75to79_2024 is not-actionable, rsv_pretend_clinical_cohort are not-eligible",
        ),
        (
            ["rsv_75_rolling", "rsv_75to79_2024", "rsv_pretend_clinical_cohort"],
            [
                (
                    "rsv_age_range",
                    "rsv_age_range positive description",
                    ["Excluded postcode In SW19", "Excluded postcode In SW19"],
                ),
                ("rsv_clinical_cohort", "rsv_clinical_cohort positive description", ["Excluded postcode In SW19"]),
            ],
            "all are not-actionable",
        ),
    ],
)
def test_cohort_groups_and_their_descriptions_and_the_collection_of_s_rules_when_best_status_is_not_actionable(
    person_cohorts: list[str],
    expected_cohort_group_and_description_and_s_rule_names: list[tuple[str, str, list[str]]],
    test_comment: str,
    faker: Faker,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=person_cohorts, postcode="SW19")
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.Rsv75RollingCohortFactory.build(),
                        rule_builder.Rsv75to79CohortFactory.build(),
                        rule_builder.RsvPretendClinicalCohortFactory.build(),
                    ],
                    iteration_rules=[rule_builder.PostcodeSuppressionRuleFactory.build()],
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
                .and_status(Status.not_actionable)
                .and_cohort_results(
                    contains_exactly(
                        *[
                            is_cohort_result()
                            .with_cohort_code(item[0])
                            .and_description(item[1])
                            .and_reasons(
                                contains_exactly(*[is_reason().with_rule_name(rule_name) for rule_name in item[2]])
                            )
                            for item in expected_cohort_group_and_description_and_s_rule_names
                        ]
                    )
                ),
            )
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("person_cohorts", "expected_cohort_group_and_description", "test_comment"),
    [
        (
            ["rsv_75_rolling"],
            [("rsv_age_range", "rsv_age_range positive description")],
            "rsv_75_rolling is actionable, others are not-eligible",
        ),
        (
            ["rsv_75_rolling", "rsv_75to79_2024"],
            [("rsv_age_range", "rsv_age_range positive description")],
            "rsv_75_rolling, rsv_75to79_2024 is actionable, rsv_pretend_clinical_cohort are not-eligible",
        ),
        (
            ["rsv_75_rolling", "rsv_75to79_2024", "rsv_pretend_clinical_cohort"],
            [
                ("rsv_age_range", "rsv_age_range positive description"),
                ("rsv_clinical_cohort", "rsv_clinical_cohort positive description"),
            ],
            "all are actionable",
        ),
    ],
)
def test_cohort_group_and_descriptions_when_best_status_is_actionable(
    person_cohorts: list[str],
    expected_cohort_group_and_description: list[tuple[str, str]],
    test_comment: str,
    faker: Faker,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=person_cohorts, postcode="hp")
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.Rsv75RollingCohortFactory.build(),
                        rule_builder.Rsv75to79CohortFactory.build(),
                        rule_builder.RsvPretendClinicalCohortFactory.build(),
                    ],
                    iteration_rules=[rule_builder.PostcodeSuppressionRuleFactory.build()],
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
                .and_status(Status.actionable)
                .and_cohort_results(
                    contains_exactly(
                        *[
                            is_cohort_result().with_cohort_code(item[0]).with_description(item[1])
                            for item in expected_cohort_group_and_description
                        ]
                    )
                )
            )
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("person_rows", "expected_description", "test_comment"),
    [
        (
            person_rows_builder(nhs_number="123", cohorts=[]),
            "rsv_age_range negative description 1",
            "status - not eligible",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling", "rsv_75to79_2024"], postcode="SW19"),
            "rsv_age_range positive description 1",
            "status - not actionable",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling", "rsv_75to79_2024"], postcode="hp"),
            "rsv_age_range positive description 1",
            "status - actionable",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75to79_2024"], postcode="hp"),
            "rsv_age_range positive description 2",
            "rsv_75to79_2024 - actionable and rsv_75_rolling is not eligible",
        ),
    ],
)
def test_cohort_group_descriptions_are_selected_based_on_priority_when_cohorts_have_different_non_empty_descriptions(
    person_rows: list[dict[str, Any]], expected_description: str, test_comment: str
):
    # Given
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.Rsv75to79CohortFactory.build(
                            positive_description=rules.Description("rsv_age_range positive description 2"),
                            negative_description=rules.Description("rsv_age_range negative description 2"),
                            priority=2,
                        ),
                        rule_builder.Rsv75RollingCohortFactory.build(
                            positive_description=rules.Description("rsv_age_range positive description 1"),
                            negative_description=rules.Description("rsv_age_range negative description 1"),
                            priority=1,
                        ),
                    ],
                    iteration_rules=[rule_builder.PostcodeSuppressionRuleFactory.build()],
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
                .and_cohort_results(
                    contains_exactly(
                        is_cohort_result().with_cohort_code("rsv_age_range").with_description(expected_description)
                    )
                )
            )
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("person_rows", "iteration_cohorts", "expected_cohort_group_and_description", "expected_status", "test_comment"),
    [
        (
            person_rows_builder("123", postcode="SW19", cohorts=[], de=False),
            [rule_builder.Rsv75to79CohortFactory.build(negative_description=None, priority=2)],
            [("rsv_age_range", "")],
            Status.not_eligible,
            "if group has one cohort, with no description, expect no description",
        ),
        (
            person_rows_builder("123", postcode="SW19", cohorts=["rsv_75to79_2024", "rsv_75_rolling"], de=False),
            [rule_builder.Rsv75to79CohortFactory.build(negative_description=None, priority=2)],
            [("rsv_age_range", "")],
            Status.not_eligible,
            "if group has one cohort, with no description, expect no description",
        ),
        (
            person_rows_builder("123", postcode="HP1", cohorts=["rsv_75to79_2024", "rsv_75_rolling"], de=True),
            [rule_builder.Rsv75to79CohortFactory.build(positive_description=None, priority=2)],
            [("rsv_age_range", "")],
            Status.not_actionable,
            "if group has one cohort, with no description, expect no description",
        ),
        (
            person_rows_builder("123", postcode="HP1", cohorts=["rsv_75to79_2024", "rsv_75_rolling"], de=False),
            [rule_builder.Rsv75to79CohortFactory.build(positive_description=None, priority=2)],
            [("rsv_age_range", "")],
            Status.actionable,
            "if group has one cohort, with no description, expect no description",
        ),
        (
            person_rows_builder("123", postcode="SW19", cohorts=[], de=False),
            [
                rule_builder.Rsv75to79CohortFactory.build(priority=2, negative_description=None),
                rule_builder.Rsv75RollingCohortFactory.build(priority=3, negative_description="rsv age range -ve 1"),
                rule_builder.Rsv75RollingCohortFactory.build(
                    cohort_label="rsv_75_rolling_2", priority=4, negative_description="rsv age range -ve 2"
                ),
            ],
            [("rsv_age_range", "rsv age range -ve 1")],
            Status.not_eligible,
            "if group has more than one cohort, at least one has description, expect first non empty description",
        ),
        (
            person_rows_builder("123", postcode="SW19", cohorts=["rsv_75to79_2024", "rsv_75_rolling"], de=False),
            [
                rule_builder.Rsv75to79CohortFactory.build(priority=2, negative_description=None),
                rule_builder.Rsv75RollingCohortFactory.build(priority=3, negative_description="rsv age range -ve 1"),
                rule_builder.Rsv75RollingCohortFactory.build(
                    cohort_label="rsv_75_rolling_2", priority=4, negative_description="rsv age range -ve 2"
                ),
            ],
            [("rsv_age_range", "rsv age range -ve 1")],
            Status.not_eligible,
            "if group has more than one cohort, at least one has description, expect first non empty description",
        ),
        (
            person_rows_builder("123", postcode="HP1", cohorts=["rsv_75to79_2024", "rsv_75_rolling"], de=True),
            [
                rule_builder.Rsv75to79CohortFactory.build(priority=2, positive_description=None),
                rule_builder.Rsv75RollingCohortFactory.build(priority=3, positive_description="rsv age range +ve 1"),
                rule_builder.Rsv75RollingCohortFactory.build(
                    cohort_label="rsv_75_rolling_2", priority=4, positive_description="rsv age range +ve 2"
                ),
            ],
            [("rsv_age_range", "rsv age range +ve 1")],
            Status.not_actionable,
            "if group has more than one cohort, at least one has description, expect first non empty description",
        ),
        (
            person_rows_builder("123", postcode="HP1", cohorts=["rsv_75to79_2024", "rsv_75_rolling"], de=False),
            [
                rule_builder.Rsv75to79CohortFactory.build(priority=2, positive_description=None),
                rule_builder.Rsv75RollingCohortFactory.build(priority=3, positive_description="rsv age range +ve 1"),
                rule_builder.Rsv75RollingCohortFactory.build(
                    cohort_label="rsv_75_rolling_2", priority=4, positive_description="rsv age range +ve 2"
                ),
            ],
            [("rsv_age_range", "rsv age range +ve 1")],
            Status.actionable,
            "if group has more than one cohort, at least one has description, expect first non empty description",
        ),
    ],
)
def test_cohort_group_descriptions_pick_first_non_empty_if_available(
    person_rows: list[dict[str, Any]],
    iteration_cohorts: list[rules.IterationCohort],
    expected_cohort_group_and_description: list[tuple[str, str]],
    expected_status: Status,
    test_comment: str,
):
    # Given
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=iteration_cohorts,
                    iteration_rules=[
                        rule_builder.PostcodeSuppressionRuleFactory.build(type=rules.RuleType.filter),
                        rule_builder.DetainedEstateSuppressionRuleFactory.build(),
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
                .and_status(expected_status)
                .and_cohort_results(
                    contains_exactly(
                        *[
                            is_cohort_result()
                            .with_cohort_code(item[0])
                            .with_description(item[1])
                            .with_status(expected_status)
                            for item in expected_cohort_group_and_description
                        ]
                    )
                )
            )
        ),
        test_comment,
    )


book_nbs_comms = AvailableAction(
    ActionType="ButtonAuthLink",
    ExternalRoutingCode="BookNBS",
    ActionDescription="Action description",
    UrlLink="http://www.nhs.uk/book-rsv",
    UrlLabel="Continue to booking",
)

default_comms_detail = AvailableAction(
    ActionType="CareCardWithText",
    ExternalRoutingCode="BookLocal",
    ActionDescription="You can get an RSV vaccination at your GP surgery",
)

suggested_action_for_book_nbs = SuggestedAction(
    action_type=ActionType(book_nbs_comms.action_type),
    action_code=ActionCode(book_nbs_comms.action_code),
    action_description=ActionDescription(book_nbs_comms.action_description),
    url_link=UrlLink(book_nbs_comms.url_link),
    url_label=UrlLabel(book_nbs_comms.url_label),
)

suggested_action_for_default_comms = SuggestedAction(
    action_type=ActionType(default_comms_detail.action_type),
    action_code=ActionCode(default_comms_detail.action_code),
    action_description=ActionDescription(default_comms_detail.action_description),
    url_link=None,
    url_label=None,
)


@pytest.mark.parametrize(
    ("test_comment", "default_comms_routing", "comms_routing", "actions_mapper", "expected_actions"),
    [
        (
            """Rule match: default_comms_routing present, action_mapper present,
                return actions from matching comms from rule""",
            "defaultcomms",
            "InternalBookNBS",
            {"InternalBookNBS": book_nbs_comms, "defaultcomms": default_comms_detail},
            SuggestedActions([suggested_action_for_book_nbs]),
        ),
        (
            """Rule match: default_comms_routing has multiple values,
                comms missing in rule, all default comms should be returned in actions""",
            "defaultcomms1|defaultcomms2",
            None,
            {"defaultcomms1": default_comms_detail, "defaultcomms2": default_comms_detail},
            SuggestedActions([suggested_action_for_default_comms, suggested_action_for_default_comms]),
        ),
        (
            """Rule match: default_comms_routing has multiple values,
                comms is empty string, all default comms should be returned in actions""",
            "defaultcomms1",
            "",
            {"defaultcomms1": default_comms_detail},
            SuggestedActions([suggested_action_for_default_comms]),
        ),
        (
            """Rule match: default_comms_routing present,
                action_mapper missing for matching comms, return default_comms in actions""",
            "defaultcomms",
            "InternalBookNBS",
            {"defaultcomms": default_comms_detail},
            SuggestedActions([suggested_action_for_default_comms]),
        ),
        (
            """Rule match: default_comms_routing present,
                rule has an incorrect comms key, return default_comms in actions""",
            "defaultcomms",
            "InvalidCode",
            {"defaultcomms": default_comms_detail},
            SuggestedActions([suggested_action_for_default_comms]),
        ),
        (
            """Rule match: action_mapper present without url,
                return actions from matching comms from rule""",
            "defaultcomms",
            "InternalBookNBS",
            {
                "InternalBookNBS": AvailableAction(
                    ActionType=book_nbs_comms.action_type,
                    ExternalRoutingCode=book_nbs_comms.action_code,
                    ActionDescription=book_nbs_comms.action_description,
                )
            },
            SuggestedActions(
                [
                    SuggestedAction(
                        action_type=ActionType(book_nbs_comms.action_type),
                        action_code=ActionCode(book_nbs_comms.action_code),
                        action_description=ActionDescription(book_nbs_comms.action_description),
                        url_link=None,
                        url_label=None,
                    )
                ]
            ),
        ),
        (
            """Rule match: default_comms_routing missing,
                comms present in rule, action_mapper missing, return no actions""",
            "",
            "InternalBookNBS",
            {},
            SuggestedActions([]),
        ),
        (
            """Rule match: default_comms_routing missing, but action_mapper present,
                return actions from matching comms from rule""",
            "",
            "InternalBookNBS",
            {"InternalBookNBS": book_nbs_comms},
            SuggestedActions([suggested_action_for_book_nbs]),
        ),
        (
            """Rule match: default_comms_routing present,
                comms present in rule, but action_mapper missing, return no actions""",
            "defaultcommskeywithoutactionmapper",
            "InternalBookNBS",
            {},
            SuggestedActions([]),
        ),
        (
            """Rule match: default_comms_routing has multiple values,
                one of the value is invalid, valid values should be returned in actions""",
            "defaultcomms1|invaliddefault",
            None,
            {"defaultcomms1": default_comms_detail},
            SuggestedActions([suggested_action_for_default_comms]),
        ),
    ],
)
def test_correct_actions_determined_from_redirect_r_rules(  # noqa: PLR0913
    test_comment: str,
    default_comms_routing: str,
    comms_routing: str,
    actions_mapper: ActionsMapper,
    expected_actions: SuggestedActions,
    faker: Faker,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb="QE1")

    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        default_comms_routing=default_comms_routing,
                        actions_mapper=rule_builder.ActionsMapperFactory.build(root=actions_mapper),
                        iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(comms_routing=comms_routing)],
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
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.actionable))
                .and_actions(equal_to(expected_actions))
            )
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("test_comment", "redirect_r_rule_cohort_label"),
    [
        ("cohort_label matches person cohort, result action ActionCode1", "cohort1"),
        ("cohort_label NOT matches person cohort, result action ActionCode1", "cohort2"),
    ],
)
def test_cohort_label_not_supported_used_in_r_rules(test_comment: str, redirect_r_rule_cohort_label: str, faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb="QE1")
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        default_comms_routing="defaultcomms",
                        actions_mapper=rule_builder.ActionsMapperFactory.build(
                            root={
                                "ActionCode1": book_nbs_comms,
                                "defaultcomms": default_comms_detail,
                            }
                        ),
                        iteration_rules=[
                            rule_builder.ICBRedirectRuleFactory.build(
                                cohort_label=rules.CohortLabel(redirect_r_rule_cohort_label)
                            )
                        ],
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
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.actionable))
                .and_actions(equal_to(SuggestedActions([suggested_action_for_book_nbs])))
            )
        ),
        test_comment,
    )


def test_multiple_r_rules_match_with_same_priority(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb="QE1")
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        default_comms_routing="defaultcomms",
                        actions_mapper=rule_builder.ActionsMapperFactory.build(
                            root={
                                "rule_1_comms_routing": book_nbs_comms,
                                "rule_2_comms_routing": book_nbs_comms,
                                "rule_3_comms_routing": book_nbs_comms,
                                "defaultcomms": default_comms_detail,
                            }
                        ),
                        iteration_rules=[
                            rule_builder.ICBRedirectRuleFactory.build(comms_routing="rule_1_comms_routing"),
                            rule_builder.ICBRedirectRuleFactory.build(comms_routing="rule_2_comms_routing"),
                            rule_builder.ICBRedirectRuleFactory.build(
                                priority=2,
                                attribute_name=rules.RuleAttributeName("ICBMismatch"),
                                comms_routing="rule_3_comms_routing",
                            ),
                        ],
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
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.actionable))
                .and_actions(equal_to(SuggestedActions([suggested_action_for_book_nbs])))
            )
        ),
    )


def test_multiple_r_rules_with_same_priority_one_rule_mismatch_should_return_default_comms(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb="QE1")
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        default_comms_routing="defaultcomms",
                        actions_mapper=rule_builder.ActionsMapperFactory.build(
                            root={
                                "rule_1_comms_routing": book_nbs_comms,
                                "rule_2_comms_routing": book_nbs_comms,
                                "rule_3_comms_routing": book_nbs_comms,
                                "defaultcomms": default_comms_detail,
                            }
                        ),
                        iteration_rules=[
                            rule_builder.ICBRedirectRuleFactory.build(comms_routing="rule_1_comms_routing"),
                            rule_builder.ICBRedirectRuleFactory.build(comms_routing="rule_2_comms_routing"),
                            rule_builder.ICBRedirectRuleFactory.build(
                                attribute_name=rules.RuleAttributeName("ICBMismatch"),
                                comms_routing="rule_3_comms_routing",
                            ),
                        ],
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
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.actionable))
                .and_actions(equal_to(SuggestedActions([suggested_action_for_default_comms])))
            )
        ),
    )


def test_only_highest_priority_rule_is_applied_and_return_actions_only_for_that_rule(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb="QE1")
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        default_comms_routing="defaultcomms",
                        actions_mapper=rule_builder.ActionsMapperFactory.build(
                            root={
                                "rule_1_comms_routing": AvailableAction(
                                    ActionType="ButtonAuthLink",
                                    ExternalRoutingCode="BookNBS",
                                    ActionDescription="Action description",
                                ),
                                "rule_2_comms_routing": AvailableAction(
                                    ActionType="AuthLink",
                                    ExternalRoutingCode="BookNBS",
                                    ActionDescription="Action description",
                                    UrlLink="http://www.nhs.uk/book-rsv",
                                    UrlLabel="Continue to booking",
                                ),
                                "defaultcomms": default_comms_detail,
                            }
                        ),
                        iteration_rules=[
                            rule_builder.ICBRedirectRuleFactory.build(priority=2, comms_routing="rule_2_comms_routing"),
                            rule_builder.ICBRedirectRuleFactory.build(priority=1, comms_routing="rule_1_comms_routing"),
                        ],
                    )
                ],
            )
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility()

    expected_actions = SuggestedAction(
        action_type=ActionType("ButtonAuthLink"),
        action_code=ActionCode("BookNBS"),
        action_description=ActionDescription("Action description"),
        url_link=None,
        url_label=None,
    )

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.actionable))
                .and_actions(equal_to(SuggestedActions([expected_actions])))
            )
        ),
    )


def test_should_include_actions_when_include_actions_flag_is_true_when_status_is_actionable(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb="QE1")
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        default_comms_routing="defaultcomms",
                        actions_mapper=rule_builder.ActionsMapperFactory.build(
                            root={
                                "book_nbs": book_nbs_comms,
                                "defaultcomms": default_comms_detail,
                            }
                        ),
                        iteration_rules=[
                            rule_builder.ICBRedirectRuleFactory.build(priority=2, comms_routing="book_nbs"),
                        ],
                    )
                ],
            )
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility(include_actions_flag=True)

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.actionable))
                .and_actions(equal_to(SuggestedActions([suggested_action_for_book_nbs])))
            )
        ),
    )


def test_should_not_include_actions_when_include_actions_flag_is_false_when_status_is_actionable(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=["cohort1"], icb="QE1")
    campaign_configs = [
        (
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                        default_comms_routing="defaultcomms",
                        actions_mapper=rule_builder.ActionsMapperFactory.build(
                            root={
                                "book_nbs": book_nbs_comms,
                                "defaultcomms": default_comms_detail,
                            }
                        ),
                        iteration_rules=[
                            rule_builder.ICBRedirectRuleFactory.build(priority=2, comms_routing="book_nbs"),
                        ],
                    )
                ],
            )
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.evaluate_eligibility(include_actions_flag=False)

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition()
                .with_condition_name(ConditionName("RSV"))
                .and_status(equal_to(Status.actionable))
                .and_actions(equal_to(None))
            )
        ),
    )
