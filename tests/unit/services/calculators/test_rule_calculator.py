from unittest.mock import patch

import pytest

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import IterationRule, RuleAttributeLevel
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


@patch.object(RuleCalculator, "get_attribute_value")
@patch.object(RuleCalculator, "evaluate_rule")
def test_returns_expected_status_and_reason_when_rule_code_is_not_provided(
    mock_evaluate_rule, mock_get_attribute_value
):
    person_data = Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}])
    rule = rule_builder.IterationRuleFactory.build(
        attribute_level=RuleAttributeLevel.PERSON, attribute_name="POSTCODE", rule_code=None
    )
    calc = RuleCalculator(person=person_data, rule=rule)
    mock_get_attribute_value.return_value = "SW19"
    mock_evaluate_rule.return_value = (eligibility_status.Status.not_eligible, "reason", False)

    status, reason = calc.evaluate_exclusion()
    assert reason.rule_code is None
    assert status == Status.not_eligible


@patch.object(RuleCalculator, "get_attribute_value")
@patch.object(RuleCalculator, "evaluate_rule")
def test_returns_expected_status_and_reason_when_rule_code_is_provided(mock_evaluate_rule, mock_get_attribute_value):
    person_data = Person([{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}])
    rule = rule_builder.IterationRuleFactory.build(
        attribute_level=RuleAttributeLevel.PERSON, attribute_name="POSTCODE", code="post code is M4"
    )
    calc = RuleCalculator(person=person_data, rule=rule)
    mock_get_attribute_value.return_value = "SW19"
    mock_evaluate_rule.return_value = (eligibility_status.Status.not_eligible, "reason", False)

    status, reason = calc.evaluate_exclusion()
    assert reason.rule_code == "post code is M4"
    assert status == Status.not_eligible
