from unittest.mock import patch

import pytest

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import IterationRule, RuleAttributeLevel, RuleEntry, \
    RuleName, RuleCode
from eligibility_signposting_api.model.eligibility_status import Status
from eligibility_signposting_api.model.person import Person
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator
from eligibility_signposting_api.model.campaign_config import RuleText
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


@patch.object(RuleCalculator, "get_attribute_value")
@patch.object(RuleCalculator, "evaluate_rule")
def test_returns_expected_status_and_reason_when_both_rule_mapper_and_rule_code_not_provided(
    mock_evaluate_rule, mock_get_attribute_value
):
    # Given
    person_data = Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}])
    rule_name = RuleName("POSTCODE_RULE_NAME")
    rule_code = RuleCode("POSTCODE_RULE_CODE_FROM_MAPPER")

    # Create a RuleEntry that maps the rule name to a rule code
    rule_entry = RuleEntry(RuleNames=[rule_name], RuleCode=rule_code, RuleText=RuleText("some text"))
    rules_mapper = {
        "OTHER_SETTINGS": rule_entry,
        "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=RuleCode(""), RuleText=RuleText(""))
    }
    rule = rule_builder.IterationRuleFactory.build(name = "suppress postcode rule for M4s",
        attribute_level=RuleAttributeLevel.PERSON, attribute_name="POSTCODE"
    )
    # Iteration is the parent to Iteration_rules
    rule_builder.IterationFactory.build(iteration_rules=[rule], rules_mapper=rules_mapper)

    # When
    calc = RuleCalculator(person=person_data, rule=rule)
    mock_get_attribute_value.return_value = "SW19"
    mock_evaluate_rule.return_value = (eligibility_status.Status.not_eligible, "reason", False)

    # When
    status, reason = calc.evaluate_exclusion()

    # Then
    assert reason.rule_code ==  "suppress postcode rule for M4s"
    assert status == Status.not_eligible


@patch.object(RuleCalculator, "get_attribute_value")
@patch.object(RuleCalculator, "evaluate_rule")
def test_returns_expected_status_and_reason_when_rule_mapper_is_not_provided_but_rule_code_is_provided(
    mock_evaluate_rule, mock_get_attribute_value
):
    # Given
    person_data = Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}])
    rule_name = RuleName("POSTCODE_RULE_NAME")
    rule_code = RuleCode("POSTCODE_RULE_CODE_FROM_MAPPER")

    # Create a RuleEntry that maps the rule name to a rule code
    rule_entry = RuleEntry(RuleNames=[rule_name], RuleCode=rule_code, RuleText=RuleText("some text"))
    rules_mapper = {
        "OTHER_SETTINGS": rule_entry,
        "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=RuleCode(""), RuleText=RuleText(""))
    }
    rule = rule_builder.IterationRuleFactory.build(name = "suppress postcode rule for M4s",
        attribute_level=RuleAttributeLevel.PERSON, attribute_name="POSTCODE", code="postcode is M4"
    )
    # Iteration is the parent to Iteration_rules
    rule_builder.IterationFactory.build(iteration_rules=[rule], rules_mapper=rules_mapper)

    # When
    calc = RuleCalculator(person=person_data, rule=rule)
    mock_get_attribute_value.return_value = "SW19"
    mock_evaluate_rule.return_value = (eligibility_status.Status.not_eligible, "reason", False)

    # When
    status, reason = calc.evaluate_exclusion()

    # Then
    assert reason.rule_code == "postcode is M4"
    assert status == Status.not_eligible


@patch.object(RuleCalculator, "get_attribute_value")
@patch.object(RuleCalculator, "evaluate_rule")
def test_returns_expected_status_and_reason_when_rule_mapper_is_provided(
    mock_evaluate_rule, mock_get_attribute_value
):
    # Given
    person_data = Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}])
    rule_name = RuleName("POSTCODE_RULE_NAME")
    rule_code = RuleCode("POSTCODE_RULE_CODE_FROM_MAPPER")

    # Create a RuleEntry that maps the rule name to a rule code
    rule_entry = RuleEntry(RuleNames=[rule_name], RuleCode=rule_code, RuleText=RuleText("some text"))
    rules_mapper = {
        "OTHER_SETTINGS": rule_entry,
        "ALREADY_JABBED": RuleEntry(RuleNames=[], RuleCode=RuleCode(""), RuleText=RuleText(""))
    }
    rule = rule_builder.IterationRuleFactory.build(name =rule_name,
        attribute_level=RuleAttributeLevel.PERSON, attribute_name="POSTCODE", code="postcode is M4"
    )
    # Iteration is the parent to Iteration_rules
    rule_builder.IterationFactory.build(iteration_rules=[rule], rules_mapper=rules_mapper)

    # When
    calc = RuleCalculator(person=person_data, rule=rule)
    mock_get_attribute_value.return_value = "SW19"
    mock_evaluate_rule.return_value = (eligibility_status.Status.not_eligible, "reason", False)

    # When
    status, reason = calc.evaluate_exclusion()

    # Then
    assert reason.rule_code == "POSTCODE_RULE_CODE_FROM_MAPPER"
    assert status == Status.not_eligible
