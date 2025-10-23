from unittest.mock import patch

import pytest
from hamcrest import assert_that, equal_to, is_

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import (
    IterationRule,
    RuleAttributeLevel,
    RuleCode,
    RuleEntry,
    RuleName,
    RuleText,
)
from eligibility_signposting_api.model.eligibility_status import Status
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator
from tests.fixtures.builders.model import rule as rule_builder


@pytest.mark.parametrize(
    ("person_data", "rule", "expected"),
    [
        # PERSON attribute level
        (
            Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}]),
            rule_builder.IterationRuleFactory.build(
                attribute_level=RuleAttributeLevel.PERSON, attribute_name="POSTCODE"
            ),
            "SW19",
        ),
        # TARGET attribute level
        (
            Person([{"ATTRIBUTE_TYPE": "RSV", "LAST_SUCCESSFUL_DATE": "20240101"}]),
            rule_builder.IterationRuleFactory.build(
                attribute_level=RuleAttributeLevel.TARGET,
                attribute_name="LAST_SUCCESSFUL_DATE",
                attribute_target="RSV",
            ),
            "20240101",
        ),
        # COHORT attribute level
        (
            Person([{"ATTRIBUTE_TYPE": "COHORTS", "COHORT_LABEL": ""}]),
            rule_builder.IterationRuleFactory.build(
                attribute_level=RuleAttributeLevel.COHORT, attribute_name="COHORT_LABEL"
            ),
            "",
        ),
    ],
)
def test_get_attribute_value_for_all_attribute_levels(person_data: Person, rule: IterationRule, expected: str):
    # Given
    calc = RuleCalculator(person=person_data, rule=rule)
    # When
    actual = calc.get_attribute_value()
    # Then
    assert actual == expected


@pytest.mark.parametrize(
    ("mapper_rule_entry_name", "rule_code", "expected_rule_code", "expected_rule_text", "comment"),
    [
        (
            "NO_MATCHING",
            None,
            "POSTCODE_RULE_NAME",
            "POSTCODE_RULE_DESCRIPTION",
            "Neither rules_mapper nor rule code provided",
        ),
        (
            "NO_MATCHING",
            "postcode is M4",
            "postcode is M4",
            "POSTCODE_RULE_DESCRIPTION",
            "Rule code provided, rule mapper not matched",
        ),
        (
            "POSTCODE_RULE_NAME",
            "postcode is M4",
            "POSTCODE_RULE_CODE_FROM_MAPPER",
            "POSTCODE_RULE_TEXT_FROM_MAPPER",
            "rules_mapper matched, so rule code and rule text are referred from rules_mapper",
        ),
    ],
)
@patch.object(RuleCalculator, "get_attribute_value")
@patch.object(RuleCalculator, "evaluate_rule")
def test_rule_code_resolution_in_evaluate_exclusion_function_for_rule_code_input(  # noqa : PLR0913
    mock_evaluate_rule,
    mock_get_attribute_value,
    mapper_rule_entry_name,
    rule_code,
    expected_rule_code,
    expected_rule_text,
    comment,
):
    # Given
    person_data = Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}])
    rule_entry = RuleEntry(
        RuleNames=[RuleName(mapper_rule_entry_name), RuleName("ADDRESS_RULE_NAME")],
        RuleCode=RuleCode("POSTCODE_RULE_CODE_FROM_MAPPER"),
        RuleText=RuleText("POSTCODE_RULE_TEXT_FROM_MAPPER"),
    )
    rules_mapper = {
        "OTHER_SETTINGS": rule_entry,
        "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=RuleCode(""), RuleText=RuleText("")),
    }

    rule = rule_builder.IterationRuleFactory.build(
        name="POSTCODE_RULE_NAME",
        attribute_level=RuleAttributeLevel.PERSON,
        attribute_name="POSTCODE",
        code=rule_code,
        description="POSTCODE_RULE_DESCRIPTION",
    )
    rule_builder.IterationFactory.build(iteration_rules=[rule], rules_mapper=rules_mapper)

    calc = RuleCalculator(person=person_data, rule=rule)
    mock_get_attribute_value.return_value = "SW19"
    mock_evaluate_rule.return_value = (eligibility_status.Status.not_eligible, "reason", False)

    # When
    status, reason = calc.evaluate_exclusion()

    # Then
    assert_that(status, is_(Status.not_eligible))
    assert_that(reason.rule_code, equal_to(expected_rule_code), comment)
    assert_that(reason.rule_text, equal_to(expected_rule_text), comment)


@pytest.mark.parametrize(
    ("rule_mapper", "comment"),
    [
        (
            {
                "OTHER_SETTINGS": RuleEntry(
                    RuleNames=[RuleName("NOT_MATCHED")], RuleCode=RuleCode(""), RuleText=RuleText("")
                ),
                "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=RuleCode(""), RuleText=RuleText("")),
            },
            "Rule mapper not matched",
        ),
        (
            {
                "OTHER_SETTINGS": RuleEntry(RuleNames=[RuleName("NOT_MATCHED")], RuleCode=None, RuleText=None),
                "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=None, RuleText=None),
            },
            "Rule mapper not matched",
        ),
        (None, "Rule mapper None"),
    ],
)
@patch.object(RuleCalculator, "get_attribute_value")
@patch.object(RuleCalculator, "evaluate_rule")
def test_rule_code_resolution_in_evaluate_exclusion_function_for_rule_mappers_input(
    mock_evaluate_rule, mock_get_attribute_value, rule_mapper, comment
):
    # Given
    person_data = Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}])

    rule = rule_builder.IterationRuleFactory.build(
        name="POSTCODE_RULE_NAME",
        attribute_level=RuleAttributeLevel.PERSON,
        attribute_name="POSTCODE",
        code="postcode is M4",
        description="post code rule description",
    )
    rule_builder.IterationFactory.build(iteration_rules=[rule], rules_mapper=rule_mapper)

    calc = RuleCalculator(person=person_data, rule=rule)
    mock_get_attribute_value.return_value = "SW19"
    mock_evaluate_rule.return_value = (eligibility_status.Status.not_eligible, "reason", False)

    # When
    status, reason = calc.evaluate_exclusion()

    # Then
    assert_that(status, is_(Status.not_eligible))
    assert_that(reason.rule_code, equal_to("postcode is M4"), comment)
    assert_that(reason.rule_text, equal_to("post code rule description"), comment)
