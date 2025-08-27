import re

import pytest

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.eligibility_status import (
    CohortGroupResult,
    Condition,
    ConditionName,
    Reason,
    RuleDescription,
    RulePriority,
    RuleType,
    Status,
    StatusText,
)
from eligibility_signposting_api.model.person import Person
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

        assert actual == expected

    def test_deep_nesting_token_replacement(self):
        person = Person([{"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DEGREE": "DOCTOR", "QUALITY": "NICE"}])

        reason1 = Reason(
            RuleType.suppression,
            eligibility_status.RuleName("Rule1"),
            RulePriority("1"),
            RuleDescription("This is a rule."),
            matcher_matched=False,
        )
        reason2 = Reason(
            RuleType.filter,
            eligibility_status.RuleName("Rule2"),
            RulePriority("1"),
            RuleDescription("Rule [[PERSON.AGE]] here."),
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

        assert actual.cohort_results[0].description == "Results for cohort 30."
        assert actual.cohort_results[0].reasons[1].rule_description == "Rule 30 here."
        assert actual.status_text == StatusText("Everything is NICE.")

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

        with pytest.raises(ValueError, match=expected_error):
            TokenProcessor.find_and_replace_tokens(person, condition)

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
        with pytest.raises(ValueError, match=expected_error):
            TokenProcessor.find_and_replace_tokens(person, condition)

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
        with pytest.raises(ValueError, match=expected_error):
            TokenProcessor.find_and_replace_tokens(person, condition)

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
        with pytest.raises(ValueError, match=expected_error):
            TokenProcessor.find_and_replace_tokens(person, condition)

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

        assert actual.condition_name == "Last successful date: "

    def test_non_rsv_target_token_should_raise_error(self):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30"},
                {"ATTRIBUTE_TYPE": "COVID", "CONDITION_NAME": "COVID", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName("Last successful date: [[TARGET.COVID.LAST_SUCCESSFUL_DATE]]"),
            status=Status.actionable,
            status_text=StatusText("Some status"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected_error = re.escape(
            "Invalid attribute name 'LAST_SUCCESSFUL_DATE' in token '[[TARGET.COVID.LAST_SUCCESSFUL_DATE]]'."
        )
        with pytest.raises(ValueError, match=expected_error):
            TokenProcessor.find_and_replace_tokens(person, condition)

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

        assert actual.status_text == expected.status_text
        assert actual.condition_name == expected.condition_name

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

        assert actual == expected

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
                "You had your RSV vaccine on [[TARGET.RSV.LAST_SUCCESSFUL_DATE:DATE(%d %B %Y)]]"
            ),
            status=Status.actionable,
            status_text=StatusText("Your birthday is on [[PERSON.DATE_OF_BIRTH:DATE(%-d %B %Y)]]"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        expected = Condition(
            condition_name=ConditionName("You had your RSV vaccine on 01 January 2025"),
            status=Status.actionable,
            status_text=StatusText("Your birthday is on 27 March 1990"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert actual.condition_name == expected.condition_name
        assert actual.status_text == expected.status_text

    @pytest.mark.parametrize(
        "token_format",
        [
            ":INVALID_DATE_FORMATTER(%ABC)",
            ":INVALID_DATE_FORMATTER(19900327)",
            ":()",
            ":FORMAT(DATE)",
            ":FORMAT(BLAH)",
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

        with pytest.raises(ValueError, match="Invalid token format."):
            TokenProcessor.find_and_replace_tokens(person, condition)

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
                {"ATTRIBUTE_TYPE": "RSV", "CONDITION_NAME": "RSV", "LAST_SUCCESSFUL_DATE": "19900327"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName(f"Date: [[TARGET.RSV.LAST_SUCCESSFUL_DATE{token_format}]]"),
            status=Status.actionable,
            status_text=StatusText("Some text"),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        actual = TokenProcessor.find_and_replace_tokens(person, condition)

        assert actual.condition_name == f"Date: {expected}"

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            ("[[person.DATE_OF_BIRTH:DATE(%d %B %Y)]]", "27 March 1990"),
            ("[[PERSON.date_of_birth:DATE(%d %B %Y)]]", "27 March 1990"),
            ("[[PERSON.DATE_OF_BIRTH:date(%d %B %Y)]]", "27 March 1990"),
            ("[[pErSoN.DATE_OF_BIRTH:DATE(%d %B %Y)]]", "27 March 1990"),
            ("[[target.RSV.LAST_SUCCESSFUL_DATE:DATE(%-d %B %Y)]]", "1 January 2025"),
            ("[[TARGET.rsv.LAST_SUCCESSFUL_DATE:DATE(%-d %B %Y)]]", "1 January 2025"),
            ("[[TARGET.RSV.last_successful_date:DATE(%-d %B %Y)]]", "1 January 2025"),
            ("[[TARGET.RSV.last_successful_date:date(%-d %B %Y)]]", "1 January 2025"),
        ],
    )
    def test_token_replace_is_case_insensitive(self, token: str, expected: str):
        person = Person(
            [
                {"ATTRIBUTE_TYPE": "PERSON", "AGE": "30", "DATE_OF_BIRTH": "19900327"},
                {"ATTRIBUTE_TYPE": "RSV", "CONDITION_NAME": "RSV", "LAST_SUCCESSFUL_DATE": "20250101"},
            ]
        )

        condition = Condition(
            condition_name=ConditionName(f"RSV vaccine on: {token}."),
            status=Status.actionable,
            status_text=StatusText(f"Your DOB is: {token}."),
            cohort_results=[],
            suitability_rules=[],
            actions=[],
        )

        result = TokenProcessor.find_and_replace_tokens(person, condition)

        assert result.status_text == f"Your DOB is: {expected}."
        assert result.condition_name == f"RSV vaccine on: {expected}."
