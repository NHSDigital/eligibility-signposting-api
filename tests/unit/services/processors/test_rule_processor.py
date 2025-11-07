from unittest.mock import Mock, patch

import pytest
from hamcrest import assert_that, empty, is_

from eligibility_signposting_api.model.campaign_config import CohortLabel, IterationCohort, RuleType
from eligibility_signposting_api.model.eligibility_status import CohortGroupResult, Reason, RuleName, Status
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.person_data_reader import PersonDataReader
from eligibility_signposting_api.services.processors.rule_processor import RuleProcessor
from tests.fixtures.builders.model import rule as rule_builder
from tests.fixtures.builders.model.eligibility import ReasonFactory


@pytest.fixture
def mock_person_data_reader():
    return Mock(spec=PersonDataReader)


@pytest.fixture
def rule_processor(mock_person_data_reader):
    return RuleProcessor(mock_person_data_reader)


MOCK_PERSON_DATA = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])


def test_get_exclusion_rules_no_rules():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    rules_to_filter = []
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([]))


def test_get_exclusion_rules_general_rule():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    no_cohort_label_rule = rule_builder.IterationRuleFactory.build(cohort_label=None)
    rules_to_filter = [no_cohort_label_rule]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([no_cohort_label_rule]))


def test_get_exclusion_rules_matching_cohort_label():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_A")
    rules_to_filter = [matching_rule]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([matching_rule]))


def test_get_exclusion_rules_matching_cohort_label_when_it_contains_multiple_cohort_labels():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_A,COHORT_B")
    rules_to_filter = [matching_rule]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([matching_rule]))


def test_get_exclusion_rules_non_matching_cohort_label():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    non_matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B")
    rules_to_filter = [non_matching_rule]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([]))


def test_get_exclusion_rules_non_matching_cohort_label_when_it_contains_multiple_cohort_labels():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    non_matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B,COHORT_C")
    rules_to_filter = [non_matching_rule]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([]))


def test_get_exclusion_rules_matching_from_list_cohort_label():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    rule1 = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_A")
    rule2 = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B")
    rules_to_filter = [rule1, rule2]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([rule1]))


def test_get_exclusion_rules_matching_from_list_cohort_label_when_it_contains_multiple_cohort_labels():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    rule1 = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_A")
    rule2 = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B,COHORT_C")
    rules_to_filter = [rule1, rule2]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that(result, is_([rule1]))


def test_get_exclusion_rules_mixed_rules():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    no_cohort_label_rule = rule_builder.IterationRuleFactory.build(cohort_label=None, name="General")
    matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_A", name="Matching")
    non_matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B", name="NonMatching")

    rules_to_filter = [no_cohort_label_rule, matching_rule, non_matching_rule]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that({r.name for r in result}, is_({"General", "Matching"}))


def test_get_exclusion_rules_mixed_rules_when_it_contains_multiple_cohort_labels():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    no_cohort_label_rule = rule_builder.IterationRuleFactory.build(cohort_label=None, name="General")
    matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_A,COHORT_C", name="Matching")
    non_matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B,COHORT_C", name="NonMatching")

    rules_to_filter = [no_cohort_label_rule, matching_rule, non_matching_rule]
    result = list(RuleProcessor.get_exclusion_rules(cohort, rules_to_filter))
    assert_that({r.name for r in result}, is_({"General", "Matching"}))


@patch("eligibility_signposting_api.services.processors.rule_processor.RuleCalculator")
def test_evaluate_rules_priority_group_all_actionable(mock_rule_calculator_class, rule_processor):
    mock_rule_calculator_class.return_value.evaluate_exclusion.return_value = (
        Status.actionable,
        Mock(spec=Reason, matcher_matched=False),
    )

    rule1 = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter)
    rule2 = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter)
    rules_group = iter([rule1, rule2])

    status, reasons, is_rule_stop = rule_processor.evaluate_rules_priority_group(MOCK_PERSON_DATA, rules_group)

    assert_that(status, is_(Status.actionable))
    assert_that(reasons, is_([]))
    assert_that(is_rule_stop, is_(False))
    assert_that(mock_rule_calculator_class.call_count, is_(2))


@patch("eligibility_signposting_api.services.processors.rule_processor.RuleCalculator")
def test_evaluate_rules_priority_group_one_not_eligible(mock_rule_calculator_class, rule_processor):
    mock_rule_calculator_class.side_effect = [
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(spec=Reason, matcher_matched=False)))),
        Mock(
            evaluate_exclusion=Mock(
                return_value=(
                    Status.not_eligible,
                    ReasonFactory.build(rule_name="ExclusionReason", matcher_matched=True),
                )
            )
        ),
    ]

    rule1 = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter, name="Rule1")
    rule2 = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter, name="Rule2")
    rules_group = iter([rule1, rule2])

    status, reasons, is_rule_stop = rule_processor.evaluate_rules_priority_group(MOCK_PERSON_DATA, rules_group)

    assert_that(status, is_(Status.actionable))
    assert_that(len(reasons), is_(1))
    assert_that(reasons[0].rule_name, is_(RuleName("ExclusionReason")))
    assert_that(is_rule_stop, is_(False))
    assert_that(mock_rule_calculator_class.call_count, is_(2))


@patch("eligibility_signposting_api.services.processors.rule_processor.RuleCalculator")
def test_evaluate_rules_priority_group_with_rule_stop(mock_rule_calculator_class, rule_processor):
    mock_rule_calculator_class.side_effect = [
        Mock(evaluate_exclusion=Mock(return_value=(Status.actionable, Mock(spec=Reason, matcher_matched=False)))),
        Mock(
            evaluate_exclusion=Mock(
                return_value=(Status.not_eligible, ReasonFactory.build(rule_name="StopReason", matcher_matched=True))
            )
        ),
    ]

    rule1 = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.suppression, rule_stop=False)
    rule2 = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.suppression, rule_stop=True)
    rules_group = iter([rule1, rule2])

    status, reasons, is_rule_stop = rule_processor.evaluate_rules_priority_group(MOCK_PERSON_DATA, rules_group)

    assert_that(status, is_(Status.actionable))
    assert_that(len(reasons), is_(1))
    assert_that(is_rule_stop, is_(True))


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
def test_general_suppression_rule_should_not_evaluate_in_isolation_without_matching_specific_rule(
    mock_evaluate_rules_priority_group,
    rule_processor,
):
    # Person is in COHORT_B
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_B", positive_description="Eligible")
    cohort_results = {}

    # Rule 1: Non-matching rule cohort-specific to COHORT_A — should not be evaluated
    rule_specific = rule_builder.IterationRuleFactory.build(
        priority=510, type=RuleType.suppression, cohort_label="COHORT_A", name="SPECIFIC_RULE"
    )

    # Rule 2: Matching general rule of the same priority as cohort-specific rule
    # - should also not be evaluated
    rule_general = rule_builder.IterationRuleFactory.build(
        priority=510, type=RuleType.suppression, cohort_label=None, name="GENERAL_RULE"
    )

    suppression_rules = [rule_specific, rule_general]

    # Act
    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    # None of the rules should be evaluated
    mock_evaluate_rules_priority_group.assert_not_called()
    # Cohort remains actionable
    assert_that(cohort_results["COHORT_B"].status, is_(Status.actionable))


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
def test_general_filter_rule_should_not_evaluate_in_isolation_without_matching_specific_rule(
    mock_evaluate_rules_priority_group,
    rule_processor,
):
    # Person is in COHORT_B
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_B", positive_description="Eligible")
    cohort_results = {}

    # Rule 1: Non-matching rule cohort-specific to COHORT_A — should not be evaluated
    rule_specific = rule_builder.IterationRuleFactory.build(
        priority=510, type=RuleType.filter, cohort_label="COHORT_A", name="SPECIFIC_RULE"
    )

    # Rule 2: Matching general rule of the same priority as cohort-specific rule
    # - should also not be evaluated
    rule_general = rule_builder.IterationRuleFactory.build(
        priority=510, type=RuleType.filter, cohort_label=None, name="GENERAL_RULE"
    )

    filter_rules = [rule_specific, rule_general]

    # Act
    rule_processor.is_eligible(MOCK_PERSON_DATA, cohort, cohort_results, filter_rules)

    # None of the rules should be evaluated
    mock_evaluate_rules_priority_group.assert_not_called()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_is_eligible_by_filter_rules_eligible(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    cohort_results = {}
    filter_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter)
    filter_rules = [filter_rule]

    mock_evaluate_rules_priority_group.return_value = (Status.actionable, [], False)

    is_eligible = rule_processor.is_eligible(MOCK_PERSON_DATA, cohort, cohort_results, filter_rules)

    assert_that(is_eligible, is_(True))
    assert_that(cohort_results, is_({}))
    mock_should_skip_rule_group.assert_called_once_with(cohort, filter_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_is_eligible_by_filter_rules_not_eligible(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A", negative_description="Not Eligible")
    cohort_results = {}
    filter_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter, name="F1")
    filter_rules = [filter_rule]
    mock_reason = ReasonFactory.build(rule_name="F1_Reason")

    mock_evaluate_rules_priority_group.return_value = (Status.not_eligible, [mock_reason], False)

    is_eligible = rule_processor.is_eligible(MOCK_PERSON_DATA, cohort, cohort_results, filter_rules)

    assert_that(is_eligible, is_(False))
    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_eligible))
    assert_that(cohort_results["COHORT_A"].description, is_("Not Eligible"))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason]))
    mock_should_skip_rule_group.assert_called_once_with(cohort, filter_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_evaluate_suppression_rules_actionable(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A", positive_description="Actionable")
    cohort_results = {}
    suppression_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.suppression)
    suppression_rules = [suppression_rule]

    mock_evaluate_rules_priority_group.return_value = (Status.actionable, [], False)

    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.actionable))
    assert_that(cohort_results["COHORT_A"].description, is_("Actionable"))
    assert_that(cohort_results["COHORT_A"].reasons, is_([]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([]))
    mock_should_skip_rule_group.assert_called_once_with(cohort, suppression_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_evaluate_suppression_rules_not_actionable(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(
        cohort_label="COHORT_A", positive_description="Positive Description"
    )
    cohort_results = {}
    suppression_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.suppression, name="S1")
    suppression_rules = [suppression_rule]
    mock_reason = ReasonFactory.build(rule_name="S1_Reason")

    mock_evaluate_rules_priority_group.return_value = (Status.not_actionable, [mock_reason], False)

    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_actionable))
    assert_that(cohort_results["COHORT_A"].description, is_("Positive Description"))
    assert_that(cohort_results["COHORT_A"].reasons, is_([mock_reason]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason]))
    mock_should_skip_rule_group.assert_called_once_with(cohort, suppression_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_evaluate_suppression_rules_stops_on_rule_stop(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    cohort_results = {}
    suppression_rule_p1 = rule_builder.IterationRuleFactory.build(
        priority=1, type=RuleType.suppression, rule_stop=True, name="S1"
    )
    suppression_rule_p2 = rule_builder.IterationRuleFactory.build(priority=2, type=RuleType.suppression, name="S2")
    suppression_rules = [suppression_rule_p1, suppression_rule_p2]

    mock_reason_p1 = ReasonFactory.build(rule_name="S1_Reason")
    mock_reason_p2 = ReasonFactory.build(rule_name="S2_Reason")

    mock_evaluate_rules_priority_group.side_effect = [
        (Status.not_actionable, [mock_reason_p1], True),
        (Status.not_actionable, [mock_reason_p2], False),
    ]

    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_actionable))
    assert_that(cohort_results["COHORT_A"].reasons, is_([mock_reason_p1]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason_p1]))
    assert_that(mock_evaluate_rules_priority_group.call_count, is_(1))
    mock_should_skip_rule_group.assert_called_once_with(cohort, [suppression_rule_p1])


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_evaluate_suppression_rules_does_not_stop_on_rule_stop_when_status_is_actionable(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    cohort_results = {}
    suppression_rule_p1 = rule_builder.IterationRuleFactory.build(
        priority=1, type=RuleType.suppression, rule_stop=True, name="S1"
    )
    suppression_rule_p2 = rule_builder.IterationRuleFactory.build(priority=2, type=RuleType.suppression, name="S2")
    suppression_rules = [suppression_rule_p1, suppression_rule_p2]

    mock_reason_p1 = ReasonFactory.build(rule_name="S1_Reason")
    mock_reason_p2 = ReasonFactory.build(rule_name="S2_Reason")

    mock_evaluate_rules_priority_group.side_effect = [
        (Status.actionable, [mock_reason_p1], True),
        (Status.not_actionable, [mock_reason_p2], False),
    ]

    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_actionable))
    assert_that(cohort_results["COHORT_A"].reasons, is_([mock_reason_p2]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason_p2]))

    assert_that(mock_evaluate_rules_priority_group.call_count, is_(2))
    assert_that(mock_should_skip_rule_group.call_count, is_(2))


def test_is_base_eligible(mock_person_data_reader):
    person = Person(
        [
            {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"},
            {
                "ATTRIBUTE_TYPE": "COHORTS",
                "COHORT_MEMBERSHIPS": [
                    {"COHORT_LABEL": "COHORT_A"},
                    {"COHORT_LABEL": "COHORT_C"},
                ],
            },
        ]
    )

    rule_processor = RuleProcessor(mock_person_data_reader)
    mock_person_data_reader.get_person_cohorts.return_value = {"COHORT_A", "COHORT_C"}

    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")

    assert_that(rule_processor.is_base_eligible(person, cohort), is_(True))
    mock_person_data_reader.get_person_cohorts.assert_called_once_with(person)


def test_is_not_base_eligible(mock_person_data_reader):
    person = Person(
        [
            {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"},
            {
                "ATTRIBUTE_TYPE": "COHORTS",
                "COHORT_MEMBERSHIPS": [
                    {"COHORT_LABEL": "COHORT_C"},
                ],
            },
        ]
    )

    rule_processor = RuleProcessor(mock_person_data_reader)
    mock_person_data_reader.get_person_cohorts.return_value = {"COHORT_C"}

    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")

    assert_that(rule_processor.is_base_eligible(person, cohort), is_(False))
    mock_person_data_reader.get_person_cohorts.assert_called_once_with(person)


def test_rules_get_group_by_types_of_rules(rule_processor):
    active_iteration = rule_builder.IterationFactory.build()
    iteration_rules = active_iteration.iteration_rules
    iteration_rules.append(rule_builder.IterationRuleFactory.build())

    iteration_rules[0].type = RuleType.filter
    iteration_rules[1].type = RuleType.suppression
    iteration_rules[2].type = RuleType.filter

    rules_by_type = rule_processor.get_rules_by_type(active_iteration)

    assert_that(len(rules_by_type), is_(2))

    assert_that(rules_by_type[0][0].type, is_(RuleType.filter))
    assert_that(rules_by_type[0][1].type, is_(RuleType.filter))
    assert_that(rules_by_type[1][0].type, is_(RuleType.suppression))


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_is_eligible_by_filter_rules(mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    cohort_results = {}
    filter_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter)
    filter_rules = [filter_rule]

    mock_evaluate_rules_priority_group.return_value = (Status.actionable, [], False)

    is_eligible = rule_processor.is_eligible(MOCK_PERSON_DATA, cohort, cohort_results, filter_rules)

    assert_that(is_eligible, is_(True))
    assert_that(cohort_results, is_({}))
    mock_should_skip_rule_group.assert_called_once_with(cohort, filter_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_is_not_eligible_by_filter_rules(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A", negative_description="Not Eligible")
    cohort_results = {}
    filter_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter, name="F1")
    filter_rules = [filter_rule]
    mock_reason = ReasonFactory.build(rule_name="F1_Reason")

    def mock_evaluate_side_effect(person, rules_group):  # noqa: ARG001
        cohort_results[cohort.cohort_label] = CohortGroupResult(
            cohort.cohort_group,
            Status.not_eligible,
            [],
            cohort.negative_description,
            [mock_reason],
        )
        return Status.not_eligible, [mock_reason], False

    mock_evaluate_rules_priority_group.side_effect = mock_evaluate_side_effect

    is_eligible = rule_processor.is_eligible(MOCK_PERSON_DATA, cohort, cohort_results, filter_rules)

    assert_that(is_eligible, is_(False))
    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_eligible))
    assert_that(cohort_results["COHORT_A"].description, is_("Not Eligible"))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason]))
    mock_should_skip_rule_group.assert_called_once_with(cohort, filter_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_is_actionable_by_suppression_rules(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A", positive_description="Actionable")
    cohort_results = {}
    suppression_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.suppression)
    suppression_rules = [suppression_rule]

    mock_evaluate_rules_priority_group.return_value = (Status.actionable, [], False)

    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.actionable))
    assert_that(cohort_results["COHORT_A"].description, is_("Actionable"))
    assert_that(cohort_results["COHORT_A"].reasons, is_(empty()))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_(empty()))
    mock_should_skip_rule_group.assert_called_once_with(cohort, suppression_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "_should_skip_rule_group", return_value=False)
def test_is_not_actionable_by_suppression_rules(
    mock_should_skip_rule_group, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(
        cohort_label="COHORT_A", positive_description="Positive Description"
    )
    cohort_results = {}
    suppression_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.suppression, name="S1")
    suppression_rules = [suppression_rule]
    mock_reason = ReasonFactory.build(rule_name="S1_Reason")

    def mock_evaluate_side_effect(person, rules_group):  # noqa: ARG001
        cohort_results[cohort.cohort_label] = CohortGroupResult(
            cohort.cohort_group,
            Status.not_actionable,
            [mock_reason],
            cohort.positive_description,
            [mock_reason],
        )
        return Status.not_actionable, [mock_reason], False

    mock_evaluate_rules_priority_group.side_effect = mock_evaluate_side_effect

    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    assert_that(len(cohort_results), is_(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_actionable))
    assert_that(cohort_results["COHORT_A"].description, is_("Positive Description"))
    assert_that(cohort_results["COHORT_A"].reasons, is_([mock_reason]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason]))
    mock_should_skip_rule_group.assert_called_once_with(cohort, suppression_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "get_rules_by_type")
@patch("eligibility_signposting_api.services.processors.rule_processor.BaseEligibilityHandler")
@patch("eligibility_signposting_api.services.processors.rule_processor.FilterRuleHandler")
@patch("eligibility_signposting_api.services.processors.rule_processor.SuppressionRuleHandler")
def test_get_cohort_group_results(
    mock_suppression_handler_class,
    mock_filter_handler_class,
    mock_base_handler_class,
    mock_get_rules_by_type,
    rule_processor,
):
    mock_base_handler_instance = mock_base_handler_class.return_value
    mock_filter_handler_instance = mock_filter_handler_class.return_value
    mock_suppression_handler_instance = mock_suppression_handler_class.return_value

    mock_base_handler_instance.next.return_value = mock_filter_handler_instance
    mock_filter_handler_instance.next.return_value = mock_suppression_handler_instance

    cohort_a = rule_builder.IterationCohortFactory.build(
        cohort_label="COHORT_A", priority=1, cohort_group="common_cohort"
    )
    cohort_b = rule_builder.IterationCohortFactory.build(
        cohort_label="COHORT_B", priority=2, cohort_group="common_cohort"
    )
    active_iteration = rule_builder.IterationFactory.build(
        iteration_cohorts=[cohort_a, cohort_b],
        iteration_rules=[
            rule_builder.IterationRuleFactory.build(type=RuleType.filter, priority=1),
            rule_builder.IterationRuleFactory.build(type=RuleType.suppression, priority=1),
        ],
    )

    filter_rules = (rule_builder.IterationRuleFactory.build(type=RuleType.filter),)
    suppression_rules = (rule_builder.IterationRuleFactory.build(type=RuleType.suppression),)
    mock_get_rules_by_type.return_value = (filter_rules, suppression_rules)

    def mock_handle_side_effect(
        person: Person,  # noqa: ARG001
        cohort: IterationCohort,
        cohort_results: dict[CohortLabel, CohortGroupResult],
        rule_processor_instance: RuleProcessor,  # noqa: ARG001
    ):
        if cohort.cohort_label == CohortLabel("COHORT_A"):
            cohort_results[CohortLabel("COHORT_A")] = CohortGroupResult(
                cohort_code=cohort.cohort_group,
                status=Status.actionable,
                reasons=[],
                description="Cohort A Description",
                audit_rules=[],
            )
        elif cohort.cohort_label == CohortLabel("COHORT_B"):
            cohort_results[CohortLabel("COHORT_B")] = CohortGroupResult(
                cohort_code=cohort.cohort_group,
                status=Status.not_eligible,
                reasons=[],
                description="Cohort B Description",
                audit_rules=[],
            )

    mock_base_handler_instance.handle.side_effect = mock_handle_side_effect

    result = rule_processor.get_cohort_group_results(MOCK_PERSON_DATA, active_iteration)

    mock_get_rules_by_type.assert_called_once_with(active_iteration)

    mock_base_handler_class.assert_called_once_with()
    mock_filter_handler_class.assert_called_once_with(filter_rules=filter_rules)
    mock_suppression_handler_class.assert_called_once_with(suppression_rules=suppression_rules)

    mock_base_handler_instance.next.assert_called_once_with(mock_filter_handler_instance)
    mock_filter_handler_instance.next.assert_called_once_with(mock_suppression_handler_instance)

    assert_that(mock_base_handler_instance.handle.call_count, is_(2))
    calls = mock_base_handler_instance.handle.call_args_list
    assert_that(calls[0].args[1], is_(cohort_a))
    assert_that(calls[1].args[1], is_(cohort_b))

    assert_that(len(result), is_(2))
    expected_result = {
        CohortLabel("COHORT_A"): CohortGroupResult(
            cohort_code=cohort_a.cohort_group,
            status=Status.actionable,
            reasons=[],
            description="Cohort A Description",
            audit_rules=[],
        ),
        CohortLabel("COHORT_B"): CohortGroupResult(
            cohort_code=cohort_b.cohort_group,
            status=Status.not_eligible,
            reasons=[],
            description="Cohort B Description",
            audit_rules=[],
        ),
    }
    assert_that(result, is_(expected_result))

    assert_that(result[CohortLabel("COHORT_A")].status, is_(Status.actionable))
    assert_that(result[CohortLabel("COHORT_B")].status, is_(Status.not_eligible))

    assert_that(result[CohortLabel("COHORT_A")].status, is_(Status.actionable))
    assert_that(result[CohortLabel("COHORT_B")].status, is_(Status.not_eligible))


@patch.object(RuleProcessor, "get_rules_by_type", return_value=((), ()))
@patch("eligibility_signposting_api.services.processors.rule_processor.BaseEligibilityHandler")
@patch("eligibility_signposting_api.services.processors.rule_processor.FilterRuleHandler")
@patch("eligibility_signposting_api.services.processors.rule_processor.SuppressionRuleHandler")
def test_get_cohort_group_results_no_rules_no_cohorts(
    mock_suppression_handler_class,
    mock_filter_handler_class,
    mock_base_handler_class,
    mock_get_rules_by_type,
    rule_processor,
):
    mock_base_handler_instance = mock_base_handler_class.return_value
    active_iteration = rule_builder.IterationFactory.build(iteration_cohorts=[], iteration_rules=[])

    result = rule_processor.get_cohort_group_results(MOCK_PERSON_DATA, active_iteration)

    mock_get_rules_by_type.assert_called_once_with(active_iteration)
    mock_base_handler_class.assert_called_once_with()
    mock_filter_handler_class.assert_called_once_with(filter_rules=())
    mock_suppression_handler_class.assert_called_once_with(suppression_rules=())

    mock_base_handler_instance.handle.assert_not_called()
    assert_that(result, is_({}))
