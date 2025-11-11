from unittest.mock import Mock

import pytest
from hamcrest import assert_that, has_length, is_

from eligibility_signposting_api.model.campaign_config import IterationCohort, IterationRule
from eligibility_signposting_api.model.eligibility_status import CohortGroupResult, Status
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.cohort_handler import (
    BaseEligibilityHandler,
    CohortEligibilityHandler,
    FilterRuleHandler,
    SuppressionRuleHandler,
)
from eligibility_signposting_api.services.processors.rule_processor import RuleProcessor
from tests.fixtures.builders.model import rule as rule_builder

MOCK_PERSON = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])


@pytest.fixture
def mock_rule_processor_for_handlers():
    return Mock(spec=RuleProcessor)


@pytest.fixture
def mock_next_handler():
    return Mock(spec=CohortEligibilityHandler)


def test_base_eligibility_handler_is_base_eligible(mock_rule_processor_for_handlers, mock_next_handler):
    handler = BaseEligibilityHandler(next_handler=mock_next_handler)
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="cohort1")
    cohort_results = {}

    mock_rule_processor_for_handlers.is_base_eligible.return_value = True

    handler.handle(MOCK_PERSON, cohort, cohort_results, mock_rule_processor_for_handlers)

    mock_rule_processor_for_handlers.is_base_eligible.assert_called_once_with(MOCK_PERSON, cohort)
    assert_that(cohort_results, is_({}))

    mock_next_handler.handle.assert_called_once_with(
        MOCK_PERSON, cohort, cohort_results, mock_rule_processor_for_handlers
    )


def test_base_eligibility_handler_is_not_base_eligible(mock_rule_processor_for_handlers, mock_next_handler):
    handler = BaseEligibilityHandler(next_handler=mock_next_handler)
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="cohort1", negative_description="Not Base eligible")
    cohort_results = {}

    mock_rule_processor_for_handlers.is_base_eligible.return_value = False

    handler.handle(MOCK_PERSON, cohort, cohort_results, mock_rule_processor_for_handlers)

    mock_rule_processor_for_handlers.is_base_eligible.assert_called_once_with(MOCK_PERSON, cohort)
    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["cohort1"].status, is_(Status.not_eligible))
    assert_that(cohort_results["cohort1"].description, is_("Not Base eligible"))
    mock_next_handler.handle.assert_not_called()


def test_filter_rule_handler_is_eligible(mock_rule_processor_for_handlers, mock_next_handler):
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="cohort1")
    cohort_results = {}
    filter_rules = [Mock()]
    handler = FilterRuleHandler(next_handler=mock_next_handler, filter_rules=filter_rules)

    mock_rule_processor_for_handlers.is_eligible.return_value = True

    handler.handle(MOCK_PERSON, cohort, cohort_results, mock_rule_processor_for_handlers)

    mock_rule_processor_for_handlers.is_eligible.assert_called_once_with(
        MOCK_PERSON, cohort, cohort_results, filter_rules
    )
    assert_that(cohort_results, is_({}))

    mock_next_handler.handle.assert_called_once_with(
        MOCK_PERSON, cohort, cohort_results, mock_rule_processor_for_handlers
    )


def test_filter_rule_handler_is_not_eligible(mock_rule_processor_for_handlers, mock_next_handler):
    filter_rules = [Mock()]
    handler = FilterRuleHandler(next_handler=mock_next_handler, filter_rules=filter_rules)
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="cohort1", negative_description="Not Eligible")
    cohort_results = {}

    def mark_not_eligible_side_effect(
        person: Person,  # noqa : ARG001
        context: IterationCohort,
        results: dict[str, CohortGroupResult],
        rules: list[IterationRule],  # noqa : ARG001
    ) -> bool:
        results.update(
            {
                context.cohort_label: CohortGroupResult(
                    context.cohort_group, Status.not_eligible, [], context.negative_description, []
                )
            }
        )
        return False

    mock_rule_processor_for_handlers.is_eligible.side_effect = mark_not_eligible_side_effect

    handler.handle(MOCK_PERSON, cohort, cohort_results, mock_rule_processor_for_handlers)

    mock_rule_processor_for_handlers.is_eligible.assert_called_once_with(
        MOCK_PERSON, cohort, cohort_results, filter_rules
    )
    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["cohort1"].status, is_(Status.not_eligible))
    mock_next_handler.handle.assert_not_called()


def test_suppression_rule_handler_is_actionable(mock_rule_processor_for_handlers):
    suppression_rules = [Mock()]
    handler = SuppressionRuleHandler(suppression_rules=suppression_rules)
    cohort = rule_builder.IterationCohortFactory.build(cohort_label="cohort1", positive_description="Actionable")
    cohort_results = {}

    def mark_actionable_side_effect(
        person: Person,  # noqa : ARG001
        context: IterationCohort,
        results: dict[str, CohortGroupResult],
        rules: list[IterationRule],  # noqa : ARG001
    ) -> None:
        results.update(
            {
                context.cohort_label: CohortGroupResult(
                    context.cohort_group, Status.actionable, [], context.positive_description, []
                )
            }
        )

    mock_rule_processor_for_handlers.is_actionable.side_effect = mark_actionable_side_effect

    handler.handle(MOCK_PERSON, cohort, cohort_results, mock_rule_processor_for_handlers)

    mock_rule_processor_for_handlers.is_actionable.assert_called_once_with(
        MOCK_PERSON, cohort, cohort_results, suppression_rules
    )
    assert_that(cohort_results, has_length(1))
    assert_that(cohort_results["cohort1"].status, is_(Status.actionable))
