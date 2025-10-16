import datetime
import logging
from typing import Any

import pytest
from faker import Faker
from flask import Flask, g
from freezegun import freeze_time
from hamcrest import assert_that, contains_exactly, contains_inanyorder, has_item, has_items, is_, is_in
from pydantic import HttpUrl

from eligibility_signposting_api.model import campaign_config, eligibility_status
from eligibility_signposting_api.model import campaign_config as rules_model
from eligibility_signposting_api.model.campaign_config import (
    AvailableAction,
    CohortLabel,
    Description,
    RuleAttributeLevel,
    RuleAttributeName,
    RuleAttributeTarget,
    RuleComparator,
    RuleName,
    RuleOperator,
    RuleType,
)
from eligibility_signposting_api.model.eligibility_status import (
    ActionCode,
    ActionDescription,
    ActionType,
    CohortGroupResult,
    Condition,
    ConditionName,
    DateOfBirth,
    InternalActionCode,
    IterationResult,
    NHSNumber,
    Postcode,
    Reason,
    RuleDescription,
    RulePriority,
    Status,
    StatusText,
    SuggestedAction,
)
from eligibility_signposting_api.services.calculators.eligibility_calculator import EligibilityCalculator
from tests.fixtures.builders.model import rule as rule_builder
from tests.fixtures.builders.model.eligibility import ReasonFactory
from tests.fixtures.builders.repos.person import person_rows_builder
from tests.fixtures.matchers.eligibility import (
    is_cohort_result,
    is_condition,
    is_eligibility_status,
)


@pytest.fixture
def app():
    return Flask(__name__)


@pytest.mark.parametrize(
    ("person_cohorts", "iteration_cohorts_and_virtual_flag", "status", "test_comment"),
    [
        (["cohort1"], {"cohort2": "Y"}, Status.actionable, "a virtual cohort"),
        (["cohort1"], {"cohort1": "Y"}, Status.actionable, "a virtual cohort that is in person cohort"),
        (["cohort1"], {"cohort1": "N"}, Status.actionable, "a non-virtual cohort that is in person cohort"),
        (["cohort1"], {"cohort2": "N"}, Status.not_eligible, "a non-virtual cohort that is not in person cohort"),
        (
            ["cohort1"],
            {"cohort1": "N", "cohort2": "Y"},
            Status.actionable,
            "one virtual cohort, other is non virtual & in person cohort",
        ),
        (
            ["cohort1"],
            {"cohort1": "Y", "cohort2": "N"},
            Status.actionable,
            "one non virtual cohort, other is virtual & in person cohort",
        ),
        (
            ["cohort1"],
            {"cohort2": "y", "cohort3": "y"},
            Status.actionable,
            "two virtual cohorts, neither of them is in person cohort",
        ),
        (
            ["cohort1", "cohort2"],
            {"cohort1": "y", "cohort2": "y"},
            Status.actionable,
            "two virtual cohorts, both are in person cohort",
        ),
        (
            ["cohort1"],
            {"cohort2": "N", "cohort3": "N"},
            Status.not_eligible,
            "two not virtual cohorts, neither of them is in person cohort",
        ),
        ([], {"cohort1": "Y"}, Status.actionable, "No person cohorts. Only virtual cohort"),
        ([], {"cohort1": "N"}, Status.not_eligible, "No person cohorts. Only non-virtual cohort"),
    ],
)
def test_base_eligible_with_when_virtual_cohort_is_present(
    faker: Faker,
    person_cohorts: list[str],
    iteration_cohorts_and_virtual_flag: dict[str, str],
    status: Status,
    test_comment: str,
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
                        rule_builder.IterationCohortFactory.build(cohort_label=label, virtual=flag.upper())
                        for label, flag in iteration_cohorts_and_virtual_flag.items()
                    ],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(status))
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    "iteration_type",
    ["A", "M", "S", "O"],
)
def test_campaigns_with_applicable_iteration_types_in_campaign_level_considered(iteration_type: str, faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())

    person_rows = person_rows_builder(nhs_number, cohorts=[])
    campaign_configs = [rule_builder.CampaignConfigFactory.build(target="RSV", iteration_type=iteration_type)]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

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
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_actionable))
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
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
        test_comment,
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
        nhs_number, cohorts=["cohort1"], vaccines={vaccine: {"LAST_SUCCESSFUL_DATE": last_successful_date}}
    )

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_rules=[
                        rule_builder.IterationRuleFactory.build(
                            type=RuleType.suppression,
                            name=RuleName("You have already been vaccinated against RSV in the last year"),
                            description=RuleDescription("Exclude anyone Completed RSV Vaccination in the last year"),
                            priority=10,
                            operator=RuleOperator.day_gte,
                            attribute_level=RuleAttributeLevel.TARGET,
                            attribute_name=RuleAttributeName("LAST_SUCCESSFUL_DATE"),
                            comparator=RuleComparator("-365"),
                            attribute_target=RuleAttributeTarget("RSV"),
                        ),
                        rule_builder.IterationRuleFactory.build(
                            type=RuleType.suppression,
                            name=RuleName("You have a vaccination date in the future for RSV"),
                            description=RuleDescription("Exclude anyone with future Completed RSV Vaccination"),
                            priority=10,
                            operator=RuleOperator.day_lte,
                            attribute_level=RuleAttributeLevel.TARGET,
                            attribute_name=RuleAttributeName("LAST_SUCCESSFUL_DATE"),
                            comparator=RuleComparator("0"),
                            attribute_target=RuleAttributeTarget("RSV"),
                        ),
                    ],
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(target_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

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
        (["cohort3", "cohort2"], Status.actionable, "cohort1 is not eligible, cohort 2 is actionable"),
        (["cohort1"], Status.not_actionable, "cohort1 is not actionable"),
        (["cohort3"], Status.not_eligible, "cohort1 and cohort 2 are not eligible"),
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
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
        test_comment,
    )


@pytest.mark.parametrize(
    ("iteration_cohorts_with_virtual_flag", "iteration_rules_with_cohort_labels", "expected_statuses"),
    [
        (
            {"cohort1": "Y", "cohort2": "Y"},
            ["cohort1", "cohort2"],
            {"cohort1": Status.not_actionable, "cohort2": Status.not_actionable},
        ),
        ({"cohort1": "Y", "cohort2": "Y"}, ["cohort3"], {"cohort1": Status.actionable, "cohort2": Status.actionable}),
        (
            {"cohort1": "Y", "cohort2": "Y"},
            ["cohort1"],
            {"cohort2": Status.actionable},
        ),
        (
            {"cohort1": "Y", "cohort2": "Y"},
            ["cohort2"],
            {"cohort1": Status.actionable},
        ),
        (
            {"cohort1": "Y", "cohort2": "N"},
            ["cohort1", "cohort2"],
            {"cohort1": Status.not_actionable, "cohort2": Status.not_actionable},
        ),
        ({"cohort1": "Y", "cohort2": "N"}, ["cohort3"], {"cohort1": Status.actionable, "cohort2": Status.actionable}),
        (
            {"cohort1": "Y", "cohort2": "N"},
            ["cohort1"],
            {"cohort2": Status.actionable},
        ),
        (
            {"cohort1": "Y", "cohort2": "N"},
            ["cohort2"],
            {"cohort1": Status.actionable},
        ),
    ],
)
def test_status_if_iteration_rules_contains_virtual_cohorts_as_cohort_label_field(
    iteration_cohorts_with_virtual_flag: dict[str, str],
    iteration_rules_with_cohort_labels: list,
    expected_statuses: dict[str, Status],
    faker: Faker,
):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=66, maximum_age=74))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=["cohort1", "cohort2"],
    )
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_group=f"group_{label}", cohort_label=label, virtual=flag.upper()
                        )
                        for label, flag in iteration_cohorts_with_virtual_flag.items()
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(cohort_label=label)
                        for label in iteration_rules_with_cohort_labels
                    ],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

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
                            is_cohort_result().with_cohort_code(f"group_{cohort}").with_status(status)
                            for cohort, status in expected_statuses.items()
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
                ("virtual cohort group", "virtual negative description"),
                ("rsv_age_range", "rsv_age_range negative description"),
            ],
            "rsv_75_rolling is not base-eligible & virtual cohort group not eligible by F rules ",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="AC01", de=True, icb="QE1"),
            Status.not_eligible,
            [
                ("virtual cohort group", "virtual negative description"),
                ("rsv_age_range", "rsv_age_range negative description"),
            ],
            "all the cohorts are not-eligible by F rules",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="SW19", de=False, icb="QE1"),
            Status.not_actionable,
            [
                ("virtual cohort group", "virtual positive description"),
                ("rsv_age_range", "rsv_age_range positive description"),
            ],
            "all the cohorts are not-actionable",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="AC01", de=False, icb="QE1"),
            Status.actionable,
            [
                ("virtual cohort group", "virtual positive description"),
                ("rsv_age_range", "rsv_age_range positive description"),
            ],
            "all the cohorts are actionable",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="AC01", de=False, icb="NOT_QE1"),
            Status.actionable,
            [("virtual cohort group", "virtual positive description")],
            "virtual_cohort is actionable, but not others",
        ),
        (
            person_rows_builder(nhs_number="123", cohorts=["rsv_75_rolling"], postcode="SW19", de=False, icb="NOT_QE1"),
            Status.not_actionable,
            [("virtual cohort group", "virtual positive description")],
            "virtual_cohort is not-actionable, but others are not eligible",
        ),
    ],
)
def test_cohort_groups_and_their_descriptions_when_virtual_cohort_is_present(
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
                        rule_builder.VirtualCohortFactory.build(),
                    ],
                    iteration_rules=[
                        # F common rule
                        rule_builder.DetainedEstateSuppressionRuleFactory.build(type=RuleType.filter),
                        # F rules for rsv_75_rolling
                        rule_builder.ICBFilterRuleFactory.build(
                            type=RuleType.filter, cohort_label=CohortLabel("rsv_75_rolling")
                        ),
                        # S common rule
                        rule_builder.PostcodeSuppressionRuleFactory.build(
                            comparator=RuleComparator("SW19"),
                        ),
                    ],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

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
                            positive_description=Description("rsv_age_range positive description 2"),
                            negative_description=Description("rsv_age_range negative description 2"),
                            priority=2,
                        ),
                        rule_builder.Rsv75RollingCohortFactory.build(
                            positive_description=Description("rsv_age_range positive description 1"),
                            negative_description=Description("rsv_age_range negative description 1"),
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
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

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


@freeze_time("2025-04-25")
def test_no_active_iteration_returns_empty_conditions_with_single_active_campaign(faker: Faker):
    # Given
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()), cohorts=[])
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    name="inactive iteration",
                    iteration_rules=[],
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                )
            ],
        )
    ]
    # Need to set the iteration date to override CampaignConfigFactory.fix_iteration_date_invariants behavior
    campaign_configs[0].iterations[0].iteration_date = datetime.date(2025, 5, 10)

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(actual, is_eligibility_status().with_conditions([]))


@pytest.mark.usefixtures("caplog")
@freeze_time("2025-04-25")
def test_returns_no_condition_data_for_campaign_without_active_iteration(faker: Faker, caplog):
    # Given
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()), cohorts=[])
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    name="inactive iteration",
                    iteration_rules=[],
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    name="active iteration",
                    iteration_rules=[],
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                )
            ],
        ),
    ]
    # Need to set the iteration date to override CampaignConfigFactory.fix_iteration_date_invariants behavior
    rsv_campaign = campaign_configs[0]
    rsv_campaign.iterations[0].iteration_date = datetime.date(2025, 5, 10)

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    with caplog.at_level(logging.INFO):
        actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    condition_names = [condition.condition_name for condition in actual.conditions]

    assert ConditionName("RSV") not in condition_names
    assert ConditionName("COVID") in condition_names
    assert f"Skipping campaign ID {rsv_campaign.id} as no active iteration was found." in caplog.text


@freeze_time("2025-04-25")
def test_no_active_campaign(faker: Faker):
    # Given
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()), cohorts=[])
    campaign_configs = [rule_builder.CampaignConfigFactory.build()]
    # Need to set the campaign dates to override CampaignConfigFactory.fix_iteration_date_invariants behavior
    campaign_configs[0].start_date = datetime.date(2025, 5, 10)

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(actual, is_eligibility_status().with_conditions([]))


def test_eligibility_status_replaces_tokens_with_attribute_data(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(datetime.date(2025, 5, 10))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=["cohort_1", "cohort_2", "cohort_3"],
        vaccines={"RSV": {"LAST_SUCCESSFUL_DATE": datetime.date(2024, 1, 3).strftime("%Y%m%d")}},
        icb="QE1",
        gp_practice=None,
    )

    person_attribute_token = "DOB: [[PERSON.DATE_OF_BIRTH]]"  # noqa: S105
    target_attribute_token = "LAST_SUCCESSFUL_DATE: [[TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y)]]"  # noqa: S105
    available_action = AvailableAction(
        ActionType="ButtonAuthLink",
        ExternalRoutingCode="BookNBS",
        ActionDescription="## Get vaccinated at your GP surgery in [[PERSON.ICB]].",
        UrlLink=HttpUrl("https://www.nhs.uk/book-rsv"),
        UrlLabel="Your GP practice code is [[PERSON.GP_PRACTICE]].",
    )

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="cohort_1", positive_description=person_attribute_token
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="cohort_2", positive_description=target_attribute_token
                        ),
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(),
                        rule_builder.ICBNonActionableActionRuleFactory.build(comms_routing="TOKEN_TEST"),
                    ],
                    actions_mapper=rule_builder.ActionsMapperFactory.build(root={"TOKEN_TEST": available_action}),
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_actionable))
        ),
    )

    assert actual.conditions[0].cohort_results[0].description == "DOB: 20250510"
    assert actual.conditions[0].cohort_results[1].description == "LAST_SUCCESSFUL_DATE: 03 January 2024"
    assert actual.conditions[0].actions[0].action_description == "## Get vaccinated at your GP surgery in QE1."
    assert actual.conditions[0].actions[0].url_label == "Your GP practice code is ."

    audit_condition = g.audit_log.response.condition[0]
    assert audit_condition.eligibility_cohort_groups[0].cohort_text in [
        "DOB: 20250510",
        "LAST_SUCCESSFUL_DATE: 03 January 2024",
    ]
    assert audit_condition.eligibility_cohort_groups[1].cohort_text in [
        "DOB: 20250510",
        "LAST_SUCCESSFUL_DATE: 03 January 2024",
    ]
    assert audit_condition.actions[0].action_description == "## Get vaccinated at your GP surgery in QE1."
    assert audit_condition.actions[0].action_url_label == "Your GP practice code is ."


@pytest.mark.parametrize(
    ("rule_type", "cohorts", "expected_status"),
    [
        (RuleType.filter, ["rsv_eli_440_cohort_999"], Status.not_eligible),
        (RuleType.suppression, ["rsv_eli_440_cohort_999"], Status.not_actionable),
        (RuleType.redirect, ["rsv_eli_440_cohort_999"], Status.actionable),
        (RuleType.filter, [], Status.not_eligible),
        (RuleType.suppression, [], Status.not_actionable),
        (RuleType.redirect, [], Status.actionable),
    ],
)
def test_virtual_cohorts(faker: Faker, rule_type: RuleType, cohorts: list[str], expected_status: Status):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(datetime.date(2025, 5, 10))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=cohorts,
    )

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="elid_virtual_cohort",
                            cohort_group="elid_virtual_cohort",
                            positive_description="In elid_virtual_cohort",
                            negative_description="Out elid_virtual_cohort",
                            priority=1,
                            virtual="Y",
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_440_cohort_999",
                            cohort_group="rsv_eli_440_cohort_999",
                            positive_description="In rsv_eli_440_cohort_999",
                            negative_description="Out rsv_eli_440_cohort_999",
                            priority=2,
                        ),
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            type=rule_type,
                            name="Filter based on cohort membership",
                            description="Filter based on cohort membership.",
                            priority=100,
                            operator=RuleOperator.is_in,
                            attribute_level=RuleAttributeLevel.COHORT,
                            attribute_name="COHORT_LABEL",
                            comparator="elid_virtual_cohort",
                        ),
                    ],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(expected_status))
        ),
    )


def test_virtual_cohorts_multiple_campaigns(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(datetime.date(2025, 5, 10))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=["rsv_eli_440_cohort_999"],
    )
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="elid_virtual_cohort",
                            cohort_group="elid_virtual_cohort",
                            positive_description="In elid_virtual_cohort",
                            negative_description="Out elid_virtual_cohort",
                            priority=1,
                            virtual="Y",
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_440_cohort_999",
                            cohort_group="rsv_eli_440_cohort_999",
                            positive_description="In rsv_eli_440_cohort_999",
                            negative_description="Out rsv_eli_440_cohort_999",
                            priority=2,
                        ),
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            type=RuleType.filter,
                            name="Filter based on cohort membership",
                            description="Filter based on cohort membership.",
                            priority=100,
                            operator=RuleOperator.is_in,
                            attribute_level=RuleAttributeLevel.COHORT,
                            attribute_name="COHORT_LABEL",
                            comparator="elid_virtual_cohort",
                        ),
                    ],
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="elid_virtual_cohort",
                            cohort_group="elid_virtual_cohort",
                            positive_description="In elid_virtual_cohort",
                            negative_description="Out elid_virtual_cohort",
                            priority=1,
                            virtual="Y",
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_440_cohort_999",
                            cohort_group="rsv_eli_440_cohort_999",
                            positive_description="In rsv_eli_440_cohort_999",
                            negative_description="Out rsv_eli_440_cohort_999",
                            priority=2,
                        ),
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            type=RuleType.suppression,
                            name="Filter based on cohort membership",
                            description="Filter based on cohort membership.",
                            priority=100,
                            operator=RuleOperator.is_in,
                            attribute_level=RuleAttributeLevel.COHORT,
                            attribute_name="COHORT_LABEL",
                            comparator="elid_virtual_cohort",
                        ),
                    ],
                )
            ],
        ),
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_eligible),
                is_condition().with_condition_name(ConditionName("COVID")).and_status(Status.not_actionable),
            )
        ),
    )


def test_multiple_virtual_cohorts(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(datetime.date(2025, 5, 10))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=["rsv_eli_440_cohort_999"],
    )

    available_action = AvailableAction(
        ActionType="ButtonAuthLink",
        ExternalRoutingCode="BookNBS",
        ActionDescription="## Get vaccinated.",
        UrlLink=HttpUrl("https://www.nhs.uk/book-rsv"),
        UrlLabel="Label",
    )

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="elid_virtual_cohort",
                            cohort_group="elid_virtual_cohort",
                            positive_description="In elid_virtual_cohort",
                            negative_description="Out elid_virtual_cohort",
                            priority=1,
                            virtual="Y",
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="elid_virtual_cohort_2",
                            cohort_group="elid_virtual_cohort_2",
                            positive_description="In elid_virtual_cohort_2",
                            negative_description="Out elid_virtual_cohort_2",
                            priority=2,
                            virtual="Y",
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_440_cohort_999",
                            cohort_group="rsv_eli_440_cohort_999",
                            positive_description="In rsv_eli_440_cohort_999",
                            negative_description="Out rsv_eli_440_cohort_999",
                            priority=3,
                        ),
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            type=RuleType.filter,
                            name="Filter based on cohort membership",
                            description="Filter based on cohort membership.",
                            priority=100,
                            operator=RuleOperator.is_in,
                            attribute_level=RuleAttributeLevel.COHORT,
                            attribute_name="COHORT_LABEL",
                            comparator="elid_virtual_cohort",
                        ),
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            type=RuleType.suppression,
                            name="Filter based on cohort membership",
                            description="Filter based on cohort membership.",
                            priority=110,
                            operator=RuleOperator.is_in,
                            attribute_level=RuleAttributeLevel.COHORT,
                            attribute_name="COHORT_LABEL",
                            comparator="elid_virtual_cohort_2",
                        ),
                    ],
                    actions_mapper=rule_builder.ActionsMapperFactory.build(root={"TEST": available_action}),
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_eligible),
            )
        ),
    )


@freeze_time("2025-10-02")
def test_virtual_cohorts_when_person_has_no_existing_cohorts(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(datetime.date(1980, 10, 2))
    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=[],
        vaccines={
            "RSV": {
                "LAST_SUCCESSFUL_DATE": datetime.date(2025, 9, 25).strftime("%Y%m%d"),
                "BOOKED_APPOINTMENT_DATE": datetime.date(2025, 10, 9).strftime("%Y%m%d"),
            },
        },
    )
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_75to79",
                            cohort_group="rsv_age",
                            positive_description="In rsv_75to79",
                            negative_description="Out rsv_75to79",
                            priority=0,
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_80_since_02_Sept_2024",
                            cohort_group="rsv_age_catchup",
                            positive_description="In rsv_80_since_02_Sept_2024",
                            negative_description="Out rsv_80_since_02_Sept_2024",
                            priority=10,
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="elid_all_people",
                            cohort_group="magic_cohort",
                            positive_description="In elid_all_people",
                            negative_description="Out elid_all_people",
                            priority=20,
                            virtual="Y",
                        ),
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            attribute_level=RuleAttributeLevel.TARGET,
                            attribute_name="LAST_SUCCESSFUL_DATE",
                            attribute_target="RSV",
                            cohort_label="elid_all_people",
                            comparator="-25[[NVL:18000101]]",
                            description="Remove anyone NOT already vaccinated within the last 25 years",
                            name="Remove from magic cohort unless already vaccinated or have future booking",
                            operator=RuleOperator.year_lte,
                            priority=100,
                            type=RuleType.filter,
                        ),
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            attribute_level=RuleAttributeLevel.TARGET,
                            attribute_name="BOOKED_APPOINTMENT_DATE",
                            attribute_target="RSV",
                            cohort_label="elid_all_people",
                            comparator="0[[NVL:18000101]]",
                            description="Remove anyone without a future booking from magic cohort",
                            name="Remove from magic cohort unless already vaccinated or have future booking",
                            operator=RuleOperator.day_lt,
                            priority=110,
                            type=RuleType.filter,
                        ),
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            attribute_level=RuleAttributeLevel.TARGET,
                            attribute_name="LAST_SUCCESSFUL_DATE",
                            attribute_target="RSV",
                            comparator="-25[[NVL:18000101]]",
                            description="## You've had your RSV vaccination\n\nWe believe you had your vaccination.",
                            name="Already Vaccinated",
                            operator=RuleOperator.year_gte,
                            priority=200,
                            rule_stop=True,
                            type=RuleType.suppression,
                        ),
                    ],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_items(
                is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.not_actionable),
            )
        ),
    )


def test_regardless_of_final_status_audit_all_types_of_cohort_status_rules(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=85, maximum_age=85))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=[
            "rsv_eli_376_cohort_1",
            "rsv_eli_376_cohort_2",
            "rsv_eli_376_cohort_3",
            "rsv_eli_376_cohort_4",
            "rsv_eli_376_cohort_5",
        ],
        icb="ABC",
    )

    available_action = AvailableAction(
        ActionType="ButtonAuthLink",
        ExternalRoutingCode="BookNBS",
        ActionDescription="## Get vaccinated at your GP surgery in [[PERSON.ICB]].",
        UrlLink=HttpUrl("https://www.nhs.uk/book-rsv"),
        UrlLabel="Your GP practice code is [[PERSON.GP_PRACTICE]].",
    )

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    default_not_actionable_routing="TOKEN_TEST",
                    default_not_eligible_routing="TOKEN_TEST",
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_376_cohort_1", cohort_group="rsv_eli_376_cohort_group", priority=0
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_376_cohort_2", cohort_group="rsv_eli_376_cohort_group", priority=1
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_376_cohort_3", cohort_group="rsv_eli_376_cohort_group", priority=2
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_376_cohort_4",
                            cohort_group="rsv_eli_376_cohort_group_other",
                            priority=3,
                        ),
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="rsv_eli_376_cohort_5",
                            cohort_group="rsv_eli_376_cohort_group_another",
                            priority=4,
                        ),
                    ],
                    iteration_rules=[
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            type=RuleType.filter,
                            name=RuleName("NotEligible Reason 1"),
                            description=RuleDescription("NotEligible Description 1"),
                            priority=RulePriority("100"),
                            operator=RuleOperator.year_lte,
                            attribute_level=RuleAttributeLevel.PERSON,
                            attribute_name=RuleAttributeName("DATE_OF_BIRTH"),
                            comparator=RuleComparator("-80"),
                            cohort_label=CohortLabel("rsv_eli_376_cohort_1"),
                        ),
                        rule_builder.ICBRedirectRuleFactory.build(
                            operator=RuleOperator.ne, comparator=RuleComparator("ABC")
                        ),
                        rule_builder.PersonAgeSuppressionRuleFactory.build(
                            type=RuleType.suppression,
                            name=RuleName("NotActionable Reason 1"),
                            description=RuleDescription("NotActionable Description 1"),
                            priority=RulePriority("110"),
                            operator=RuleOperator.year_lte,
                            attribute_level=RuleAttributeLevel.PERSON,
                            attribute_name=RuleAttributeName("DATE_OF_BIRTH"),
                            comparator=RuleComparator("-80"),
                            cohort_label=CohortLabel("rsv_eli_376_cohort_5"),
                        ),
                    ],
                    actions_mapper=rule_builder.ActionsMapperFactory.build(root={"TOKEN_TEST": available_action}),
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(
        actual,
        is_eligibility_status().with_conditions(
            has_item(is_condition().with_condition_name(ConditionName("RSV")).and_status(Status.actionable))
        ),
    )

    assert len(g.audit_log.response.condition[0].filter_rules) == 1
    assert g.audit_log.response.condition[0].filter_rules[0].rule_name == "NotEligible Reason 1"
    assert g.audit_log.response.condition[0].filter_rules[0].rule_priority == "100"
    assert len(g.audit_log.response.condition[0].suitability_rules) == 1
    assert g.audit_log.response.condition[0].suitability_rules[0].rule_name == "NotActionable Reason 1"
    assert g.audit_log.response.condition[0].suitability_rules[0].rule_message == "NotActionable Description 1"
    assert g.audit_log.response.condition[0].suitability_rules[0].rule_priority == "110"


def test_eligibility_status_with_invalid_tokens_raises_attribute_error(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(datetime.date(2025, 5, 10))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=["cohort_1"],
        vaccines={"RSV": {"LAST_SUCCESSFUL_DATE": datetime.date(2024, 1, 3).strftime("%Y%m%d")}},
    )

    target_attribute_token = "LAST_SUCCESSFUL_DATE: [[TARGET.RSV.LAST_SUCCESSFUL_DATE:INVALID_DATE_FORMAT(%d %B %Y)]]"  # noqa: S105
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="cohort_1", positive_description=target_attribute_token
                        ),
                    ],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    with pytest.raises(ValueError, match="Invalid token."):
        calculator.get_eligibility_status("Y", ["ALL"], "ALL")


def test_eligibility_status_with_invalid_person_attribute_name_raises_value_error(faker: Faker):
    # Given
    nhs_number = NHSNumber(faker.nhs_number())
    date_of_birth = DateOfBirth(datetime.date(2025, 5, 10))

    person_rows = person_rows_builder(
        nhs_number,
        date_of_birth=date_of_birth,
        cohorts=["cohort_1"],
        vaccines={"RSV": {"LAST_SUCCESSFUL_DATE": datetime.date(2024, 1, 3).strftime("%Y%m%d")}},
    )

    target_attribute_token = "LAST_SUCCESSFUL_DATE: [[TARGET.RSV.ICECREAM]]"  # noqa: S105
    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    iteration_cohorts=[
                        rule_builder.IterationCohortFactory.build(
                            cohort_label="cohort_1", positive_description=target_attribute_token
                        ),
                    ],
                    iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                )
            ],
        )
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    with pytest.raises(ValueError):  # noqa: PT011
        calculator.get_eligibility_status("Y", ["ALL"], "ALL")


def test_status_text_is_used_from_campaign_when_available_for_all_statuses(faker: Faker):
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()), cohorts=["cohort1"], icb="QE1")

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[],
                    status_text=campaign_config.StatusText(
                        NotEligible="You are not eligible to take RSV vaccines.",
                        NotActionable="You have taken RSV vaccine in the last 90 days",
                        Actionable="You can take RSV vaccine.",
                    ),
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.suppression)],
                    status_text=campaign_config.StatusText(
                        NotEligible="You are not eligible to take COVID vaccines.",
                        NotActionable="You have taken COVID vaccine in the last 90 days",
                        Actionable="You can take COVID vaccine.",
                    ),
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="FLU",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.filter)],
                    status_text=campaign_config.StatusText(
                        NotEligible="You are not eligible to take FLU vaccines.",
                        NotActionable="You have taken FLU vaccine in the last 90 days",
                        Actionable="You can take FLU vaccine.",
                    ),
                )
            ],
        ),
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    rsv_condition = (
        is_condition()
        .with_condition_name(ConditionName("RSV"))
        .and_status(Status.actionable)
        .and_status_text(StatusText("You can take RSV vaccine."))
    )
    covid_condition = (
        is_condition()
        .with_condition_name(ConditionName("COVID"))
        .and_status(Status.not_actionable)
        .and_status_text(StatusText("You have taken COVID vaccine in the last 90 days"))
    )
    flu_condition = (
        is_condition()
        .with_condition_name(ConditionName("FLU"))
        .and_status(Status.not_eligible)
        .and_status_text(StatusText("You are not eligible to take FLU vaccines."))
    )

    assert_that(
        actual,
        is_eligibility_status().with_conditions(contains_inanyorder(rsv_condition, covid_condition, flu_condition)),
    )

    assert len(g.audit_log.response.condition) == len(campaign_configs)

    for condition in g.audit_log.response.condition:
        assert condition.status_text in (
            "You can take RSV vaccine.",
            "You have taken COVID vaccine in the last 90 days",
            "You are not eligible to take FLU vaccines.",
        )


def test_status_text_uses_default_when_unavailable(faker: Faker):
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()), cohorts=["cohort1"], icb="QE1")

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[],
                    status_text=None,
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.suppression)],
                    status_text=None,
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="FLU",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.filter)],
                    status_text=None,
                )
            ],
        ),
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    rsv_condition = (
        is_condition()
        .with_condition_name(ConditionName("RSV"))
        .and_status(Status.actionable)
        .and_status_text(StatusText("You should have the RSV vaccine"))
    )
    covid_condition = (
        is_condition()
        .with_condition_name(ConditionName("COVID"))
        .and_status(Status.not_actionable)
        .and_status_text(StatusText("You should have the COVID vaccine"))
    )
    flu_condition = (
        is_condition()
        .with_condition_name(ConditionName("FLU"))
        .and_status(Status.not_eligible)
        .and_status_text(StatusText("We do not believe you can have it"))
    )

    assert_that(
        actual,
        is_eligibility_status().with_conditions(contains_inanyorder(rsv_condition, covid_condition, flu_condition)),
    )

    assert len(g.audit_log.response.condition) == len(campaign_configs)

    for condition in g.audit_log.response.condition:
        assert condition.status_text in (
            "You should have the RSV vaccine",
            "You should have the COVID vaccine",
            "We do not believe you can have it",
        )


def test_status_text_uses_default_when_empty(faker: Faker):
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()), cohorts=["cohort1"], icb="QE1")
    status_text = campaign_config.StatusText(NotEligible="", NotActionable="", Actionable="")

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[],
                    status_text=status_text,
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.suppression)],
                    status_text=status_text,
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="FLU",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.filter)],
                    status_text=status_text,
                )
            ],
        ),
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    rsv_condition = (
        is_condition()
        .with_condition_name(ConditionName("RSV"))
        .and_status(Status.actionable)
        .and_status_text(StatusText("You should have the RSV vaccine"))
    )
    covid_condition = (
        is_condition()
        .with_condition_name(ConditionName("COVID"))
        .and_status(Status.not_actionable)
        .and_status_text(StatusText("You should have the COVID vaccine"))
    )
    flu_condition = (
        is_condition()
        .with_condition_name(ConditionName("FLU"))
        .and_status(Status.not_eligible)
        .and_status_text(StatusText("We do not believe you can have it"))
    )

    assert_that(
        actual,
        is_eligibility_status().with_conditions(contains_inanyorder(rsv_condition, covid_condition, flu_condition)),
    )

    assert len(g.audit_log.response.condition) == len(campaign_configs)

    for condition in g.audit_log.response.condition:
        assert condition.status_text in (
            "You should have the RSV vaccine",
            "You should have the COVID vaccine",
            "We do not believe you can have it",
        )


def test_status_text_uses_default_when_status_text_is_present_but_values_are_none(faker: Faker):
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()), cohorts=["cohort1"], icb="QE1")
    status_text = campaign_config.StatusText(NotEligible=None, NotActionable=None, Actionable=None)

    campaign_configs = [
        rule_builder.CampaignConfigFactory.build(
            target="RSV",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[],
                    status_text=status_text,
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="COVID",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.suppression)],
                    status_text=status_text,
                )
            ],
        ),
        rule_builder.CampaignConfigFactory.build(
            target="FLU",
            iterations=[
                rule_builder.IterationFactory.build(
                    default_comms_routing="TOKEN_TEST",
                    iteration_cohorts=[rule_builder.IterationCohortFactory.build(cohort_label="cohort1")],
                    iteration_rules=[rule_builder.ICBRedirectRuleFactory.build(type=RuleType.filter)],
                    status_text=status_text,
                )
            ],
        ),
    ]

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    rsv_condition = (
        is_condition()
        .with_condition_name(ConditionName("RSV"))
        .and_status(Status.actionable)
        .and_status_text(StatusText("You should have the RSV vaccine"))
    )
    covid_condition = (
        is_condition()
        .with_condition_name(ConditionName("COVID"))
        .and_status(Status.not_actionable)
        .and_status_text(StatusText("You should have the COVID vaccine"))
    )
    flu_condition = (
        is_condition()
        .with_condition_name(ConditionName("FLU"))
        .and_status(Status.not_eligible)
        .and_status_text(StatusText("We do not believe you can have it"))
    )

    assert_that(
        actual,
        is_eligibility_status().with_conditions(contains_inanyorder(rsv_condition, covid_condition, flu_condition)),
    )

    assert len(g.audit_log.response.condition) == len(campaign_configs)

    for condition in g.audit_log.response.condition:
        assert condition.status_text in (
            "You should have the RSV vaccine",
            "You should have the COVID vaccine",
            "We do not believe you can have it",
        )


class TestEligibilityResultBuilder:
    def test_build_condition_results_single_condition_single_cohort_actionable(self):
        cohort_group_results = [CohortGroupResult("COHORT_A", Status.actionable, [], "Cohort A Description", [])]
        suggested_actions = [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType("CareCardWithText"),
                action_code=ActionCode("BookLocal"),
                action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
                url_link=None,
                url_label=None,
            )
        ]
        iteration_result = IterationResult(
            Status.actionable, StatusText("You should have the RSV vaccine"), cohort_group_results, suggested_actions
        )

        result = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(result.condition_name, is_(ConditionName("RSV")))
        assert_that(result.status, is_(Status.actionable))
        assert_that(result.actions, is_(suggested_actions))
        assert_that(result.status_text, is_(Status.actionable.get_default_status_text(ConditionName("RSV"))))

        assert_that(len(result.cohort_results), is_(1))
        deduplicated_cohort = result.cohort_results[0]
        assert_that(deduplicated_cohort.cohort_code, is_("COHORT_A"))
        assert_that(deduplicated_cohort.status, is_(Status.actionable))
        assert_that(deduplicated_cohort.reasons, is_([]))
        assert_that(deduplicated_cohort.description, is_("Cohort A Description"))
        assert_that(deduplicated_cohort.audit_rules, is_([]))
        assert_that(result.suitability_rules, is_([]))

    def test_build_condition_results_single_condition_single_cohort_not_eligible_with_reasons(self):
        cohort_group_results = [CohortGroupResult("COHORT_A", Status.not_eligible, [], "Cohort A Description", [])]
        suggested_actions = [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType("CareCardWithText"),
                action_code=ActionCode("BookLocal"),
                action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
                url_link=None,
                url_label=None,
            )
        ]
        iteration_result = IterationResult(
            Status.not_eligible,
            StatusText("We do not believe you can have it"),
            cohort_group_results,
            suggested_actions,
        )

        result = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(result.condition_name, is_(ConditionName("RSV")))
        assert_that(result.status, is_(Status.not_eligible))
        assert_that(result.actions, is_(suggested_actions))
        assert_that(result.status_text, is_(Status.not_eligible.get_default_status_text(ConditionName("RSV"))))

        assert_that(len(result.cohort_results), is_(1))
        deduplicated_cohort = result.cohort_results[0]
        assert_that(deduplicated_cohort.cohort_code, is_("COHORT_A"))
        assert_that(deduplicated_cohort.status, is_(Status.not_eligible))
        assert_that(deduplicated_cohort.reasons, is_([]))
        assert_that(deduplicated_cohort.description, is_("Cohort A Description"))
        assert_that(deduplicated_cohort.audit_rules, is_([]))
        assert_that(result.suitability_rules, is_([]))

    def test_build_condition_results_single_condition_multiple_cohorts_same_cohort_code_same_status(self):
        reason_1 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Filter Rule 1"),
            RulePriority("1"),
            RuleDescription("Filter Rule Description 2"),
            matcher_matched=True,
        )
        reason_2 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Filter Rule 2"),
            RulePriority("2"),
            RuleDescription("Filter Rule Description 2"),
            matcher_matched=True,
        )
        cohort_group_results = [
            CohortGroupResult("COHORT_A", Status.not_eligible, [reason_1], "", []),
            # The below description will be picked up as the first one is empty
            CohortGroupResult("COHORT_A", Status.not_eligible, [reason_2], "Cohort A Description 2", []),
            CohortGroupResult("COHORT_A", Status.not_eligible, [], "Cohort A Description 3", []),
        ]
        suggested_actions = [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType("CareCardWithText"),
                action_code=ActionCode("BookLocal"),
                action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
                url_link=None,
                url_label=None,
            )
        ]
        iteration_result = IterationResult(Status.not_eligible, None, cohort_group_results, suggested_actions)

        result: Condition = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(len(result.cohort_results), is_(1))

        deduplicated_cohort = result.cohort_results[0]
        assert_that(deduplicated_cohort.cohort_code, is_("COHORT_A"))
        assert_that(deduplicated_cohort.status, is_(Status.not_eligible))
        assert_that(deduplicated_cohort.reasons, contains_inanyorder(reason_1, reason_2))
        assert_that(deduplicated_cohort.description, is_("Cohort A Description 2"))
        assert_that(deduplicated_cohort.audit_rules, is_([]))
        assert_that(result.suitability_rules, contains_inanyorder(reason_1, reason_2))

    def test_build_condition_results_multiple_cohorts_different_cohort_code_same_status(self):
        reason_1 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Filter Rule 1"),
            RulePriority("1"),
            RuleDescription("Filter Rule Description 2"),
            matcher_matched=True,
        )
        reason_2 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Filter Rule 2"),
            RulePriority("2"),
            RuleDescription("Filter Rule Description 2"),
            matcher_matched=True,
        )
        cohort_group_results = [
            CohortGroupResult("COHORT_X", Status.not_eligible, [reason_1], "Cohort X Description", []),
            CohortGroupResult("COHORT_Y", Status.not_eligible, [reason_2], "Cohort Y Description", []),
        ]
        suggested_actions = [
            SuggestedAction(
                internal_action_code=InternalActionCode("default_action_code"),
                action_type=ActionType("CareCardWithText"),
                action_code=ActionCode("BookLocal"),
                action_description=ActionDescription("You can get an RSV vaccination at your GP surgery"),
                url_link=None,
                url_label=None,
            )
        ]
        iteration_result = IterationResult(Status.not_eligible, None, cohort_group_results, suggested_actions)

        result = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(len(result.cohort_results), is_(2))

        expected_deduplicated_cohorts = [
            CohortGroupResult("COHORT_X", Status.not_eligible, [reason_1], "Cohort X Description", []),
            CohortGroupResult("COHORT_Y", Status.not_eligible, [reason_2], "Cohort Y Description", []),
        ]
        assert_that(result.cohort_results, contains_inanyorder(*expected_deduplicated_cohorts))

    def test_build_condition_results_cohorts_status_not_matching_iteration_status(self):
        reason_1 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Filter Rule 1"),
            RulePriority("1"),
            RuleDescription("Matching"),
            matcher_matched=True,
        )
        reason_2 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Filter Rule 2"),
            RulePriority("2"),
            RuleDescription("Not matching"),
            matcher_matched=True,
        )
        cohort_group_results = [
            CohortGroupResult("COHORT_X", Status.not_eligible, [reason_1], "Cohort X Description", []),
            CohortGroupResult("COHORT_Y", Status.not_actionable, [reason_2], "Cohort Y Description", []),
        ]

        iteration_result = IterationResult(Status.not_eligible, None, cohort_group_results, [])

        result = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(len(result.cohort_results), is_(1))
        assert_that(result.cohort_results[0].cohort_code, is_("COHORT_X"))
        assert_that(result.cohort_results[0].status, is_(Status.not_eligible))

    @pytest.mark.parametrize(
        ("reason_1", "reason_2", "reason_3", "expected_reasons"),
        [
            # Same rule name, type, and priority, different description
            (
                ReasonFactory.build(rule_description="description1", matcher_matched=True),
                ReasonFactory.build(rule_description="description2", matcher_matched=True),
                ReasonFactory.build(rule_description="description3", matcher_matched=True),
                [ReasonFactory.build(rule_description="description1", matcher_matched=True)],
            ),
            # Different rule name, same type, same priority
            (
                ReasonFactory.build(rule_name="Supress Rule 1", rule_description="description1", matcher_matched=True),
                ReasonFactory.build(rule_name="Supress Rule 2", rule_description="description2", matcher_matched=True),
                ReasonFactory.build(rule_name="Supress Rule 1", rule_description="description3", matcher_matched=True),
                [
                    ReasonFactory.build(
                        rule_name="Supress Rule 1", rule_description="description1", matcher_matched=True
                    )
                ],
            ),
            # Same rule name, same type, different priority
            (
                ReasonFactory.build(rule_priority="1", rule_description="description1", matcher_matched=True),
                ReasonFactory.build(rule_priority="2", rule_description="description2", matcher_matched=True),
                ReasonFactory.build(rule_priority="1", rule_description="description3", matcher_matched=True),
                [
                    ReasonFactory.build(rule_priority="1", rule_description="description1", matcher_matched=True),
                    ReasonFactory.build(rule_priority="2", rule_description="description2", matcher_matched=True),
                ],
            ),
            # Same rule name, same priority, different type
            (
                ReasonFactory.build(
                    rule_type=RuleType.suppression, rule_description="description1", matcher_matched=True
                ),
                ReasonFactory.build(rule_type=RuleType.filter, rule_description="description2", matcher_matched=True),
                ReasonFactory.build(
                    rule_type=RuleType.suppression, rule_description="description3", matcher_matched=True
                ),
                [
                    ReasonFactory.build(
                        rule_type=RuleType.suppression, rule_description="description1", matcher_matched=True
                    ),
                    ReasonFactory.build(
                        rule_type=RuleType.filter, rule_description="description2", matcher_matched=True
                    ),
                ],
            ),
        ],
    )
    def test_build_condition_results_grouping_reasons(self, reason_1, reason_2, reason_3, expected_reasons):
        cohort_group_results = [
            CohortGroupResult(
                "COHORT_X",
                Status.not_actionable,
                [reason_1, reason_3],
                "Cohort X Description",
                [],
            ),
            CohortGroupResult(
                "COHORT_Y",
                Status.not_actionable,
                [reason_2, reason_3],
                "Cohort Y Description",
                [],
            ),
        ]

        iteration_result = IterationResult(Status.not_actionable, None, cohort_group_results, [])

        result: Condition = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(result.suitability_rules, contains_inanyorder(*expected_reasons))

    @pytest.mark.parametrize(
        ("reason_2", "expected_reasons"),
        [
            # Same rule name, type, and priority, different description
            (
                ReasonFactory.build(
                    rule_type=RuleType.suppression,
                    rule_description="Matching",
                    rule_name="Supress Rule 1",
                    rule_priority="1",
                    matcher_matched=True,
                ),
                [
                    ReasonFactory.build(
                        rule_type=RuleType.suppression,
                        rule_description="Not matching",
                        rule_name="Supress Rule 1",
                        rule_priority="1",
                        matcher_matched=True,
                    )
                ],
            ),
            # Different rule name
            (
                ReasonFactory.build(
                    rule_type=RuleType.suppression,
                    rule_description="Matching",
                    rule_name="Supress Rule 2",
                    rule_priority="1",
                    matcher_matched=True,
                ),
                [
                    ReasonFactory.build(
                        rule_type=RuleType.suppression,
                        rule_description="Not matching",
                        rule_name="Supress Rule 1",
                        rule_priority="1",
                        matcher_matched=True,
                    )
                ],
            ),
            # Different priority
            (
                ReasonFactory.build(
                    rule_type=RuleType.suppression,
                    rule_description="Matching",
                    rule_name="Supress Rule 1",
                    rule_priority="2",
                    matcher_matched=True,
                ),
                [
                    ReasonFactory.build(
                        rule_type=RuleType.suppression,
                        rule_description="Not matching",
                        rule_name="Supress Rule 1",
                        rule_priority="1",
                        matcher_matched=True,
                    ),
                    ReasonFactory.build(
                        rule_type=RuleType.suppression,
                        rule_description="Matching",
                        rule_name="Supress Rule 1",
                        rule_priority="2",
                        matcher_matched=True,
                    ),
                ],
            ),
            # Different type
            (
                ReasonFactory.build(
                    rule_type=RuleType.filter,
                    rule_description="Matching",
                    rule_name="Supress Rule 1",
                    rule_priority="2",
                    matcher_matched=True,
                ),
                [
                    ReasonFactory.build(
                        rule_type=RuleType.suppression,
                        rule_description="Not matching",
                        rule_name="Supress Rule 1",
                        rule_priority="1",
                        matcher_matched=True,
                    ),
                    ReasonFactory.build(
                        rule_type=RuleType.filter,
                        rule_description="Matching",
                        rule_name="Supress Rule 1",
                        rule_priority="2",
                        matcher_matched=True,
                    ),
                ],
            ),
        ],
    )
    def test_build_condition_results_single_cohort(self, reason_2, expected_reasons):
        reason_1 = ReasonFactory.build(
            rule_type=RuleType.suppression,
            rule_description="Not matching",
            rule_name="Supress Rule 1",
            rule_priority="1",
            matcher_matched=True,
        )

        cohort_group_results = [
            CohortGroupResult("COHORT_Y", Status.not_actionable, [reason_1, reason_2], "Cohort Y Description", [])
        ]

        iteration_result = IterationResult(Status.not_actionable, None, cohort_group_results, [])
        result = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(len(result.cohort_results), is_(1))
        assert_that(result.cohort_results[0].reasons, contains_inanyorder(*expected_reasons))

    def test_rule_code_from_rules_mapper_is_used_when_provided(self, faker: Faker):
        # Given
        nhs_number = NHSNumber(faker.nhs_number())
        date_of_birth = DateOfBirth(faker.date_of_birth(minimum_age=76, maximum_age=79))

        person_rows = person_rows_builder(nhs_number, date_of_birth=date_of_birth, cohorts=["cohort1"])

        campaign_configs = [
            rule_builder.CampaignConfigFactory.build(
                target="RSV",
                iterations=[
                    rule_builder.IterationFactory.build(
                        default_comms_routing="TOKEN_TEST",
                        iteration_cohorts=[rule_builder.IterationCohortFactory.build()],
                        iteration_rules=[rule_builder.PersonAgeSuppressionRuleFactory.build()],
                        rules_mapper=rule_builder.RulesMapperFactory.build(),
                    )
                ],
            )
        ]

        calculator = EligibilityCalculator(person_rows, campaign_configs)

        # When
        calculator.get_eligibility_status("Y", ["ALL"], "ALL")

        # Then
