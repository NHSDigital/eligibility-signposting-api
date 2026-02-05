"""Tests for TokenProcessor with derived value support."""

import re

from hamcrest import assert_that, calling, equal_to, is_, raises

from eligibility_signposting_api.model.eligibility_status import (
    Condition,
    ConditionName,
    Status,
    StatusText,
)
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.token_processor import TokenProcessor


class TestTokenProcessorDerivedValues:
    """Tests for TokenProcessor handling derived values."""

    def test_next_dose_due_basic_replacement(self):
        """Test basic NEXT_DOSE_DUE token replacement."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("Next dose due: [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # 2025-01-01 + 91 days = 2025-04-02
        assert_that(result.status_text, is_(equal_to("Next dose due: 20250402")))

    def test_next_dose_due_with_date_format(self):
        """Test NEXT_DOSE_DUE with date formatting."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("You can book from [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91):DATE(%d %B %Y)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to("You can book from 02 April 2025")))

    def test_next_dose_due_different_days(self):
        """Test NEXT_DOSE_DUE with different number of days."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "RSV", "LAST_SUCCESSFUL_DATE": "20250601"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("RSV"),
            status=Status.actionable,
            status_text=StatusText("Next dose: [[TARGET.RSV.NEXT_DOSE_DUE:ADD_DAYS(365):DATE(%d/%m/%Y)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # 2025-06-01 + 365 days = 2026-06-01
        assert_that(result.status_text, is_(equal_to("Next dose: 01/06/2026")))

    def test_missing_vaccine_data_returns_empty(self):
        """Test that missing vaccine data returns empty string for derived values."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Next COVID dose: [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]]"),
            status=Status.actionable,
            status_text=StatusText("status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.condition_name, is_(equal_to("Next COVID dose: ")))

    def test_missing_last_successful_date_returns_empty(self):
        """Test that missing source date returns empty string."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID"},  # No LAST_SUCCESSFUL_DATE
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("Next dose: [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to("Next dose: ")))

    def test_custom_target_without_mapping_returns_empty(self):
        """Test unknown target without source override returns empty string."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("Due: [[TARGET.COVID.DOSE_DUE:ADD_DAYS(91)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to("Due: ")))

    def test_custom_target_with_source_override_uses_override(self):
        """Test custom target with explicit source override derives date."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "CUSTOM_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("Next dose: [[TARGET.COVID.DOSE_DUE:ADD_DAYS(30, CUSTOM_DATE)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to("Next dose: 20250131")))

    def test_mixed_regular_and_derived_tokens(self):
        """Test mixing regular tokens with derived value tokens."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "65"},
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText(
                "At age [[PERSON.AGE]], your next dose is from "
                "[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91):DATE(%d %B %Y)]]"
            ),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to("At age 65, your next dose is from 02 April 2025")))

    def test_unknown_function_raises_error(self):
        """Test that unknown function name raises ValueError."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("[[TARGET.COVID.SOMETHING:UNKNOWN_FUNC(123)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern="Unknown function 'UNKNOWN_FUNC'"),
        )

    def test_multiple_derived_tokens(self):
        """Test multiple derived value tokens in same text."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
                {"ATTRIBUTE_TYPE": "FLU", "LAST_SUCCESSFUL_DATE": "20250601"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Vaccines"),
            status=Status.actionable,
            status_text=StatusText(
                "COVID: [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(91)]], FLU: [[TARGET.FLU.NEXT_DOSE_DUE:ADD_DAYS(365)]]"
            ),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to("COVID: 20250402, FLU: 20260601")))

    def test_derived_value_uses_default_days_without_args(self):
        """Test that empty function args uses default days from handler config."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("Next dose: [[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS()]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # Should use the default 91 days configured in __init__.py
        # 2025-01-01 + 91 days = 2025-04-02
        assert_that(result.status_text, is_(equal_to("Next dose: 20250402")))

    def test_case_insensitive_function_name(self):
        """Test that function names are case insensitive."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("COVID"),
            status=Status.actionable,
            status_text=StatusText("[[TARGET.COVID.NEXT_DOSE_DUE:add_days(91)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to("20250402")))

    def test_not_allowed_condition_with_derived_raises_error(self):
        """Test that non-allowed conditions raise error for derived values."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "YELLOW_FEVER", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("YELLOW_FEVER"),
            status=Status.actionable,
            status_text=StatusText("[[TARGET.YELLOW_FEVER.NEXT_DOSE_DUE:ADD_DAYS(91)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected_error = re.escape(
            "Invalid attribute name 'NEXT_DOSE_DUE' in token '[[TARGET.YELLOW_FEVER.NEXT_DOSE_DUE:ADD_DAYS(91)]]'."
        )
        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=expected_error),
        )
