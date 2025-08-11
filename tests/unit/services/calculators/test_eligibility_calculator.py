import datetime
import logging
from typing import Any

import pytest
from faker import Faker
from flask import Flask
from freezegun import freeze_time
from hamcrest import assert_that, contains_exactly, contains_inanyorder, has_item, has_items, is_, is_in

from eligibility_signposting_api.model import campaign_config as rules_model
from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import (
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
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()))
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
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()))
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
    person_rows = person_rows_builder(NHSNumber(faker.nhs_number()))
    campaign_configs = [rule_builder.CampaignConfigFactory.build()]
    # Need to set the campaign dates to override CampaignConfigFactory.fix_iteration_date_invariants behavior
    campaign_configs[0].start_date = datetime.date(2025, 5, 10)

    calculator = EligibilityCalculator(person_rows, campaign_configs)

    # When
    actual = calculator.get_eligibility_status("Y", ["ALL"], "ALL")

    # Then
    assert_that(actual, is_eligibility_status().with_conditions([]))


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
        iteration_result = IterationResult(Status.actionable, cohort_group_results, suggested_actions)

        result = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(result.condition_name, is_(ConditionName("RSV")))
        assert_that(result.status, is_(Status.actionable))
        assert_that(result.actions, is_(suggested_actions))
        assert_that(result.status_text, is_(Status.actionable.get_status_text(ConditionName("RSV"))))

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
        iteration_result = IterationResult(Status.not_eligible, cohort_group_results, suggested_actions)

        result = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

        assert_that(result.condition_name, is_(ConditionName("RSV")))
        assert_that(result.status, is_(Status.not_eligible))
        assert_that(result.actions, is_(suggested_actions))
        assert_that(result.status_text, is_(Status.not_eligible.get_status_text(ConditionName("RSV"))))

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
        iteration_result = IterationResult(Status.not_eligible, cohort_group_results, suggested_actions)

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
        iteration_result = IterationResult(Status.not_eligible, cohort_group_results, suggested_actions)

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

        iteration_result = IterationResult(Status.not_eligible, cohort_group_results, [])

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
            [ReasonFactory.build(rule_name="Supress Rule 1", rule_description="description1", matcher_matched=True)],
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
            ReasonFactory.build(rule_type=RuleType.suppression, rule_description="description1", matcher_matched=True),
            ReasonFactory.build(rule_type=RuleType.filter, rule_description="description2", matcher_matched=True),
            ReasonFactory.build(rule_type=RuleType.suppression, rule_description="description3", matcher_matched=True),
            [
                ReasonFactory.build(
                    rule_type=RuleType.suppression, rule_description="description1", matcher_matched=True
                ),
                ReasonFactory.build(rule_type=RuleType.filter, rule_description="description2", matcher_matched=True),
            ],
        ),
    ],
)
def test_build_condition_results_grouping_reasons(reason_1, reason_2, reason_3, expected_reasons):
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

    iteration_result = IterationResult(Status.not_actionable, cohort_group_results, [])

    result: Condition = EligibilityCalculator.build_condition(iteration_result, ConditionName("RSV"))

    assert_that(result.suitability_rules, contains_inanyorder(*expected_reasons))
