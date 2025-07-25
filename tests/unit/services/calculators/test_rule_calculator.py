import pytest

from eligibility_signposting_api.model.campaign_config import IterationRule, RuleAttributeLevel
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
