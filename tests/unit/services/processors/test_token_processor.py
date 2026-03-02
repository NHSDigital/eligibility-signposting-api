import re

import pytest
from hamcrest import assert_that, calling, equal_to, is_, raises

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.eligibility_status import (
    CohortGroupResult,
    Condition,
    ConditionName,
    Reason,
    RulePriority,
    RuleText,
    RuleType,
    Status,
    StatusText,
)
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.processors.token_parser import ParsedToken
from eligibility_signposting_api.services.processors.token_processor import TokenProcessor


class TestTokenProcessor:
    def test_simple_token_replacement(self):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])

        condition = Condition(
            condition_name=ConditionName("RSV"),
            status=Status.actionable,
            status_text=StatusText("Your age is [[PERSON.AGE]]."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected = Condition(
            condition_name=ConditionName("RSV"),
            status=Status.actionable,
            status_text=StatusText("Your age is 30."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual, is_(equal_to(expected)))

    def test_deep_nesting_token_replacement(self):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DEGREE": "DOCTOR", "QUALITY": "NICE"}])

        reason1 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Rule1"),
            None,
            RulePriority("1"),
            RuleText("This is a rule."),
            matcher_matched=False,
        )
        reason2 = Reason(
            RuleType.filter,
            eligibility_status.RuleName("Rule2"),
            None,
            RulePriority("1"),
            RuleText("Rule [[PERSON.AGE]] here."),
            matcher_matched=True,
        )

        cohort_result = CohortGroupResult(
            cohort_code="CohortCode",
            status=Status.actionable,
            reasons=[reason1, reason2],
            description="Results for cohort [[PERSON.AGE]].",
            audit_rules=[],
        )

        condition = Condition(
            condition_name=ConditionName("ConditionName"),
            status=Status.not_actionable,
            status_text=StatusText("Everything is [[PERSON.QUALITY]]."),
            cohort_results=[cohort_result],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual.cohort_results[0].description, is_(equal_to("Results for cohort 30.")))
        assert_that(actual.cohort_results[0].reasons[1].rule_text, is_(equal_to("Rule 30 here.")))
        assert_that(actual.status_text, is_(equal_to(StatusText("Everything is NICE."))))

    def test_invalid_token_on_person_attribute_should_raise_error(self):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])

        condition = Condition(
            condition_name=ConditionName("RSV"),
            status=Status.actionable,
            status_text=StatusText("Your age is [[PERSON.ICECREAM]]."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected_error = re.escape("Invalid attribute name 'ICECREAM' in token '[[PERSON.ICECREAM]]'.")

        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=expected_error),
        )

    def test_invalid_token_should_raise_error(self):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])

        condition = Condition(
            condition_name=ConditionName("RSV"),
            status=Status.actionable,
            status_text=StatusText("Your favourite flavor is: [[ICECREAM.FLAVOR]]."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected_error = re.escape("Invalid attribute level 'ICECREAM' in token '[[ICECREAM.FLAVOR]]'.")
        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=expected_error),
        )

    def test_invalid_token_on_target_attribute_should_raise_error(self):
        person = Person([{"ATTRIBUTE_TYPE": "RSV", "LAST_SUCCESSFUL_DATE": "20250101"}])

        condition = Condition(
            condition_name=ConditionName("Condition name is [[TARGET.RSV.ICECREAM]]"),
            status=Status.actionable,
            status_text=StatusText("Some status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected_error = re.escape("Invalid attribute name 'ICECREAM' in token '[[TARGET.RSV.ICECREAM]]'.")
        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=expected_error),
        )

    def test_missing_target_attribute_and_invalid_token_should_raise_error(self):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])

        condition = Condition(
            condition_name=ConditionName("Condition name is [[TARGET.RSV.ICECREAM]]"),
            status=Status.actionable,
            status_text=StatusText("Some status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected_error = re.escape("Invalid attribute name 'ICECREAM' in token '[[TARGET.RSV.ICECREAM]]'.")
        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=expected_error),
        )

    def test_missing_patient_vaccine_data_on_target_attribute_should_replace_with_empty(self):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"}])

        condition = Condition(
            condition_name=ConditionName("Last successful date: [[TARGET.RSV.LAST_SUCCESSFUL_DATE]]"),
            status=Status.actionable,
            status_text=StatusText("Some status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual.condition_name, is_(equal_to("Last successful date: ")))

    def test_not_allowed_target_conditions_token_should_raise_error(self):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"},
                {"ATTRIBUTE_TYPE": "YELLOW_FEVER", "CONDITION_NAME": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Last successful date: [[TARGET.YELLOW_FEVER.LAST_SUCCESSFUL_DATE]]"),
            status=Status.actionable,
            status_text=StatusText("Some status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected_error = re.escape(
            "Invalid attribute name 'LAST_SUCCESSFUL_DATE' in token '[[TARGET.YELLOW_FEVER.LAST_SUCCESSFUL_DATE]]'."
        )
        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=expected_error),
        )

    def test_valid_token_but_missing_attribute_data_to_replace(self):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "POSTCODE": None},
                {"ATTRIBUTE_TYPE": "RSV", "CONDITION_NAME": "RSV", "LAST_SUCCESSFUL_DATE": None},
                {"ATTRIBUTE_TYPE": "COVID", "CONDITION_NAME": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName(
                "You had your RSV vaccine on [[TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y)]]"
            ),
            status=Status.actionable,
            status_text=StatusText("You are from [[PERSON.POSTCODE]]."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected = Condition(
            condition_name=ConditionName("You had your RSV vaccine on "),
            status=Status.actionable,
            status_text=StatusText("You are from ."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual.status_text, is_(equal_to(expected.status_text)))
        assert_that(actual.condition_name, is_(equal_to(expected.condition_name)))

    def test_valid_token_but_missing_attribute_in_multiple_vacc_data_to_replace(self):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "POSTCODE": None},
                {"ATTRIBUTE_TYPE": "RSV", "CONDITION_NAME": "RSV", "LAST_SUCCESSFUL_DATE": None},
                {"ATTRIBUTE_TYPE": "FAKEVACCS", "CONDITION_NAME": "FAKEVACCS", "LAST_SUCCESSFUL_DATE": None},
                {"ATTRIBUTE_TYPE": "COVID", "CONDITION_NAME": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
                {"ATTRIBUTE_TYPE": "FLU", "CONDITION_NAME": "FLU", "LAST_SUCCESSFUL_DATE": "20260101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName(
                "You had your COVID vaccine on [[TARGET.COVID.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y)]]"
            ),
            status=Status.actionable,
            status_text=StatusText("status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected = Condition(
            condition_name=ConditionName("You had your COVID vaccine on 01 January 2025"),
            status=Status.actionable,
            status_text=StatusText("status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual.status_text, is_(equal_to(expected.status_text)))
        assert_that(actual.condition_name, is_(equal_to(expected.condition_name)))

    def test_simple_string_with_multiple_tokens(self):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DEGREE": "DOCTOR", "QUALITY": "NICE"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("RSV"),
            status=Status.actionable,
            status_text=StatusText(
                "You are a [[PERSON.QUALITY]] [[person.QUALITY]] "
                "[[TARGET.RSV.LAST_SUCCESSFUL_DATE]] and your age is [[PERSON.AGE]]."
            ),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected = Condition(
            condition_name=ConditionName("RSV"),
            status=Status.actionable,
            status_text=StatusText("You are a NICE NICE  and your age is 30."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual, is_(equal_to(expected)))

    def test_valid_token_valid_format_should_replace_with_date_formatting(self):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DATE_OF_BIRTH": "19900327"},
                {"ATTRIBUTE_TYPE": "RSV", "CONDITION_NAME": "RSV", "LAST_SUCCESSFUL_DATE": "20250101"},
                {"ATTRIBUTE_TYPE": "COVID", "CONDITION_NAME": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName(
                "You had your COVID vaccine on [[TARGET.COVID.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y)]]"
            ),
            status=Status.actionable,
            status_text=StatusText("Your birthday is on [[PERSON.DATE_OF_BIRTH:DATE(%-d %B %Y)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected = Condition(
            condition_name=ConditionName("You had your COVID vaccine on 01 January 2025"),
            status=Status.actionable,
            status_text=StatusText("Your birthday is on 27 March 1990"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual.condition_name, is_(equal_to(expected.condition_name)))
        assert_that(actual.status_text, is_(equal_to(expected.status_text)))

    @pytest.mark.parametrize(
        "token_format",
        [
            ":()",
            ":DATE[%d %B %Y]",
            ":DATE(%A, (%d) %B %Y)",
        ],
    )
    def test_valid_token_invalid_format_should_raise_error(self, token_format: str):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DATE_OF_BIRTH": "19900327"}])

        condition = Condition(
            condition_name=ConditionName("You had your RSV vaccine"),
            status=Status.actionable,
            status_text=StatusText(f"Your birthday is on [[PERSON.DATE_OF_BIRTH{token_format}]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=r"Invalid token format\."),
        )

    @pytest.mark.parametrize(
        ("token_format", "func_name"),
        [
            (":INVALID_DATE_FORMATTER(%ABC)", "INVALID_DATE_FORMATTER"),
            (":INVALID_DATE_FORMATTER(19900327)", "INVALID_DATE_FORMATTER"),
            (":FORMAT(DATE)", "FORMAT"),
            (":FORMAT(BLAH)", "FORMAT"),
        ],
    )
    def test_unknown_function_raises_error(self, token_format: str, func_name: str):
        """Test that unknown function names raise ValueError with appropriate message."""
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DATE_OF_BIRTH": "19900327"}])

        condition = Condition(
            condition_name=ConditionName("You had your RSV vaccine"),
            status=Status.actionable,
            status_text=StatusText(f"Your birthday is on [[PERSON.DATE_OF_BIRTH{token_format}]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern=f"Unknown function '{func_name}'"),
        )

    @pytest.mark.parametrize(
        ("token_format", "expected"),
        [
            (":DATE(%d %b %Y)", "27 Mar 1990"),
            (":DATE()", ""),
            ("", "19900327"),
            (":DATE(random_value)", "random_value"),
            (":DATE(random_value %Y)", "random_value 1990"),
            (":DATE(%d %B %Y)", "27 March 1990"),
            (":DATE(%A, %d %B %Y)", "Tuesday, 27 March 1990"),
            (":DATE(%A, {%d} %B %Y)", "Tuesday, {27} March 1990"),
            (":dATE(%A, {%d} %B %Y)", "Tuesday, {27} March 1990"),
            (":date(%A, {%d} %B %Y)", "Tuesday, {27} March 1990"),
        ],
    )
    def test_valid_date_format(self, token_format: str, expected: str):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "MMR", "CONDITION_NAME": "MMR", "LAST_SUCCESSFUL_DATE": "19900327"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName(f"Date: [[TARGET.MMR.LAST_SUCCESSFUL_DATE{token_format}]]"),
            status=Status.actionable,
            status_text=StatusText("Some text"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(actual.condition_name, is_(equal_to(f"Date: {expected}")))

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            ("[[person.DATE_OF_BIRTH:DATE(%d %B %Y)]]", "27 March 1990"),
            ("[[PERSON.date_of_birth:DATE(%d %B %Y)]]", "27 March 1990"),
            ("[[PERSON.DATE_OF_BIRTH:date(%d %B %Y)]]", "27 March 1990"),
            ("[[pErSoN.DATE_OF_BIRTH:DATE(%d %B %Y)]]", "27 March 1990"),
            ("[[target.FLU.LAST_SUCCESSFUL_DATE:DATE(%-d %B %Y)]]", "1 January 2025"),
            ("[[TARGET.FLU.LAST_SUCCESSFUL_DATE:DATE(%-d %B %Y)]]", "1 January 2025"),
            ("[[TARGET.FLU.last_successful_date:DATE(%-d %B %Y)]]", "1 January 2025"),
            ("[[TARGET.FLU.last_successful_date:date(%-d %B %Y)]]", "1 January 2025"),
        ],
    )
    def test_token_replace_is_case_insensitive(self, token: str, expected: str):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DATE_OF_BIRTH": "19900327"},
                {"ATTRIBUTE_TYPE": "FLU", "CONDITION_NAME": "FLU", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName(f"FLU vaccine on: {token}."),
            status=Status.actionable,
            status_text=StatusText(f"Your DOB is: {token}."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to(f"Your DOB is: {expected}.")))
        assert_that(result.condition_name, is_(equal_to(f"FLU vaccine on: {expected}.")))


class TestCustomTargetAttributeNames:
    """Test that custom target attribute names work with derived values."""

    def test_custom_target_attribute_with_add_days_when_data_present(self):
        """Test that custom target attributes like NEXT_BOOKING_AVAILABLE work when data is present."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20260128"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText(
                "Next booking: [[TARGET.COVID.NEXT_BOOKING_AVAILABLE:ADD_DAYS(71, LAST_SUCCESSFUL_DATE)]]"
            ),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # 2026-01-28 + 71 days = 2026-04-09
        assert_that(result.status_text, is_(equal_to("Next booking: 20260409")))

    def test_custom_target_attribute_with_add_days_and_formatting(self):
        """Test that custom target attributes work with both ADD_DAYS and DATE formatting."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20260128"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText(
                "Date: [[TARGET.COVID.NEXT_BOOKING_AVAILABLE:ADD_DAYS(71, LAST_SUCCESSFUL_DATE):DATE(%d %B %Y)]]"
            ),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # 2026-01-28 + 71 days = 2026-04-09, formatted as "09 April 2026"
        assert_that(result.status_text, is_(equal_to("Date: 09 April 2026")))

    def test_custom_target_attribute_returns_empty_when_condition_not_present(self):
        """Test that custom target attributes return empty string when condition data not present."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"},
                # No COVID data present
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText(
                "Next booking: [[TARGET.COVID.NEXT_BOOKING_AVAILABLE:ADD_DAYS(71, LAST_SUCCESSFUL_DATE)]]"
            ),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # Should return empty string when condition data is not present
        assert_that(result.status_text, is_(equal_to("Next booking: ")))

    def test_multiple_custom_target_attributes_with_different_functions(self):
        """Test multiple custom target attributes with different parameters."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20260128"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText(
                "First: [[TARGET.COVID.CUSTOM_FIELD_A:ADD_DAYS(30, LAST_SUCCESSFUL_DATE)]] "
                "Second: [[TARGET.COVID.CUSTOM_FIELD_B:ADD_DAYS(60, LAST_SUCCESSFUL_DATE)]]"
            ),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # 2026-01-28 + 30 = 2026-02-27, + 60 = 2026-03-29
        assert_that(result.status_text, is_(equal_to("First: 20260227 Second: 20260329")))

    def test_custom_target_attribute_raises_error_for_invalid_condition(self):
        """Test that invalid condition names still raise errors even with custom target attributes."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText("Invalid: [[TARGET.INVALID_CONDITION.CUSTOM_FIELD:ADD_DAYS(30)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern="Invalid attribute name 'CUSTOM_FIELD'"),
        )

    def test_non_derived_token_with_invalid_target_attribute_raises_error(self):
        """Test that non-derived tokens (without functions) validate target attributes strictly."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20260128"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText("Invalid: [[TARGET.COVID.CUSTOM_INVALID_FIELD]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        # Non-derived tokens should only allow ALLOWED_TARGET_ATTRIBUTES
        assert_that(
            calling(TokenProcessor.find_and_replace_tokens).with_args(person, condition),
            raises(ValueError, pattern="Invalid attribute name 'CUSTOM_INVALID_FIELD'"),
        )

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            ("TARGET.COVID.LAST_SUCCESSFUL_DATE", 20260128),  # expect value which is an integer
            ("TARGET.COVID.SUCCESSFUL_PROCEDURE_COUNT", "3"),  # expect value which is a string
        ],
    )
    def test_non_derived_token_with_valid_target_attribute_works(self, token, expected):
        """Test that non-derived tokens with valid target attributes work correctly."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20260128", "SUCCESSFUL_PROCEDURE_COUNT": "3"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText(f"test token: [[{token}]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert_that(result.status_text, is_(equal_to(f"test token: {expected}")))

    def test_person_level_attribute_with_add_days_without_explicit_source(self):
        """Test that ADD_DAYS works on PERSON-level attributes without explicit source."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "DATE_OF_BIRTH": "19900327"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText("Future date: [[PERSON.DATE_OF_BIRTH:ADD_DAYS(91)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # 1990-03-27 + 91 days = 1990-06-26
        assert_that(result.status_text, is_(equal_to("Future date: 19900626")))

    def test_person_level_attribute_with_add_days_explicit_source(self):
        """Test that ADD_DAYS works on PERSON-level attributes with explicit source."""
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "DATE_OF_BIRTH": "19900327"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Test"),
            status=Status.actionable,
            status_text=StatusText("Future date: [[PERSON.DATE_OF_BIRTH:ADD_DAYS(91, DATE_OF_BIRTH)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        # 1990-03-27 + 91 days = 1990-06-26
        assert_that(result.status_text, is_(equal_to("Future date: 19900626")))

    def test_derived_value_with_no_function_name_raises_error(self):
        """Test that derived tokens without function name raise ValueError."""
        # This would happen if token parsing goes wrong somehow
        parsed_token = ParsedToken(
            attribute_level="TARGET",
            attribute_name="COVID",
            attribute_value="NEXT_DOSE_DUE",
            function_name=None,  # This should cause the error
            function_args=None,
            format=None,
        )

        assert_that(
            calling(TokenProcessor.get_derived_value).with_args(
                parsed_token=parsed_token,
                person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
                present_attributes={"COVID"},
                token="[[TARGET.COVID.NEXT_DOSE_DUE:]]",  # Malformed token
            ),
            raises(ValueError, pattern="No function specified in token"),
        )

    def test_derived_value_with_unknown_function_raises_error(self):
        """Test that derived tokens with unknown function raise ValueError."""
        parsed_token = ParsedToken(
            attribute_level="TARGET",
            attribute_name="COVID",
            attribute_value="NEXT_DOSE_DUE",
            function_name="UNKNOWN_FUNCTION",  # This function doesn't exist
            function_args="30",
            format=None,
        )

        assert_that(
            calling(TokenProcessor.get_derived_value).with_args(
                parsed_token=parsed_token,
                person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
                present_attributes={"COVID"},
                token="[[TARGET.COVID.NEXT_DOSE_DUE:UNKNOWN_FUNCTION(30)]]",
            ),
            raises(ValueError, pattern="Unknown function 'UNKNOWN_FUNCTION' in token"),
        )

    def test_derived_value_handler_exception_gets_wrapped(self):
        """Test that exceptions from derived value handlers are wrapped with context."""
        parsed_token = ParsedToken(
            attribute_level="TARGET",
            attribute_name="COVID",
            attribute_value="NEXT_DOSE_DUE",
            function_name="ADD_DAYS",
            function_args="invalid_arg",  # This will cause the handler to raise ValueError
            format=None,
        )

        assert_that(
            calling(TokenProcessor.get_derived_value).with_args(
                parsed_token=parsed_token,
                person_data=[{"ATTRIBUTE_TYPE": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"}],
                present_attributes={"COVID"},
                token="[[TARGET.COVID.NEXT_DOSE_DUE:ADD_DAYS(invalid_arg)]]",
            ),
            raises(ValueError, pattern=r"Error calculating derived value for token.*Invalid days argument"),
        )
