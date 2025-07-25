from unittest.mock import Mock, patch

import pytest
from hamcrest import assert_that, has_length, is_

from eligibility_signposting_api.model.campaign_config import RuleType
from eligibility_signposting_api.model.eligibility_status import Reason, Status
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.rule_processor import RuleProcessor
from tests.fixtures.builders.model import rule as rule_builder
from tests.fixtures.builders.model.eligibility import ReasonFactory


@pytest.fixture
def rule_processor():
    return RuleProcessor()


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


def test_get_exclusion_rules_non_matching_cohort_label():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    non_matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B")
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


def test_get_exclusion_rules_mixed_rules():
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    no_cohort_label_rule = rule_builder.IterationRuleFactory.build(cohort_label=None, name="General")
    matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_A", name="Matching")
    non_matching_rule = rule_builder.IterationRuleFactory.build(cohort_label="COHORT_B", name="NonMatching")

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
    assert_that(reasons, has_length(1))
    assert_that(reasons[0].rule_name, is_("ExclusionReason"))
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
    assert_that(reasons, has_length(1))
    assert_that(is_rule_stop, is_(True))


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "get_exclusion_rules", side_effect=lambda cohort, rules_to_filter: rules_to_filter)  # noqa: ARG005
def test_is_eligible_by_filter_rules_eligible(
    mock_get_exclusion_rules, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A")
    cohort_results = {}
    filter_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter)
    filter_rules = [filter_rule]

    mock_evaluate_rules_priority_group.return_value = (Status.actionable, [], False)

    is_eligible = rule_processor.is_eligible(MOCK_PERSON_DATA, cohort, cohort_results, filter_rules)

    assert_that(is_eligible, is_(True))
    assert_that(cohort_results, is_({}))
    mock_get_exclusion_rules.assert_called_once_with(cohort, filter_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "get_exclusion_rules", side_effect=lambda cohort, rules_to_filter: rules_to_filter)  # noqa: ARG005
def test_is_eligible_by_filter_rules_not_eligible(
    mock_get_exclusion_rules, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A", negative_description="Not Eligible")
    cohort_results = {}
    filter_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.filter, name="F1")
    filter_rules = [filter_rule]
    mock_reason = ReasonFactory.build(rule_name="F1_Reason")

    mock_evaluate_rules_priority_group.return_value = (Status.not_eligible, [mock_reason], False)

    is_eligible = rule_processor.is_eligible(MOCK_PERSON_DATA, cohort, cohort_results, filter_rules)

    assert_that(is_eligible, is_(False))
    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_eligible))
    assert_that(cohort_results["COHORT_A"].description, is_("Not Eligible"))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason]))
    mock_get_exclusion_rules.assert_called_once_with(cohort, filter_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "get_exclusion_rules", side_effect=lambda cohort, rules_to_filter: rules_to_filter)  # noqa: ARG005
def test_evaluate_suppression_rules_actionable(
    mock_get_exclusion_rules, mock_evaluate_rules_priority_group, rule_processor
):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="COHORT_A", positive_description="Actionable")
    cohort_results = {}
    suppression_rule = rule_builder.IterationRuleFactory.build(priority=1, type=RuleType.suppression)
    suppression_rules = [suppression_rule]

    mock_evaluate_rules_priority_group.return_value = (Status.actionable, [], False)

    rule_processor.is_actionable(MOCK_PERSON_DATA, cohort, cohort_results, suppression_rules)

    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.actionable))
    assert_that(cohort_results["COHORT_A"].description, is_("Actionable"))
    assert_that(cohort_results["COHORT_A"].reasons, is_([]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([]))
    mock_get_exclusion_rules.assert_called_once_with(cohort, suppression_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "get_exclusion_rules", side_effect=lambda cohort, rules_to_filter: rules_to_filter)  # noqa: ARG005
def test_evaluate_suppression_rules_not_actionable(
    mock_get_exclusion_rules, mock_evaluate_rules_priority_group, rule_processor
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

    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_actionable))
    assert_that(cohort_results["COHORT_A"].description, is_("Positive Description"))
    assert_that(cohort_results["COHORT_A"].reasons, is_([mock_reason]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason]))
    mock_get_exclusion_rules.assert_called_once_with(cohort, suppression_rules)
    mock_evaluate_rules_priority_group.assert_called_once()


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "get_exclusion_rules", side_effect=lambda cohort, rules_to_filter: rules_to_filter)  # noqa: ARG005
def test_evaluate_suppression_rules_stops_on_rule_stop(
    mock_get_exclusion_rules, mock_evaluate_rules_priority_group, rule_processor
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

    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_actionable))
    assert_that(cohort_results["COHORT_A"].reasons, is_([mock_reason_p1]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason_p1]))
    mock_evaluate_rules_priority_group.assert_called_once()
    mock_get_exclusion_rules.assert_called_once_with(cohort, suppression_rules)


@patch.object(RuleProcessor, "evaluate_rules_priority_group")
@patch.object(RuleProcessor, "get_exclusion_rules", side_effect=lambda cohort, rules_to_filter: rules_to_filter)  # noqa: ARG005
def test_evaluate_suppression_rules_does_not_stop_on_rule_stop_when_status_is_actionable(
    mock_get_exclusion_rules, mock_evaluate_rules_priority_group, rule_processor
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

    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["COHORT_A"].status, is_(Status.not_actionable))
    assert_that(cohort_results["COHORT_A"].reasons, is_([mock_reason_p2]))
    assert_that(cohort_results["COHORT_A"].audit_rules, is_([mock_reason_p2]))

    assert_that(mock_evaluate_rules_priority_group.call_count, is_(2))
    assert_that(mock_get_exclusion_rules.call_count, is_(1))
