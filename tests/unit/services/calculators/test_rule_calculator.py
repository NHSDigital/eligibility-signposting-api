from collections.abc import Collection, Mapping
from typing import Any

import pytest

from eligibility_signposting_api.model import rules
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator
from tests.fixtures.builders.model import rule as rule_builder

Row = Collection[Mapping[str, Any]]


@pytest.mark.parametrize(
    ("person_data", "rule", "expected"),
    [
        # PERSON attribute level
        (
            [{"ATTRIBUTE_TYPE": "PERSON", "POSTCODE": "SW19"}],
            rule_builder.IterationRuleFactory.build(
                attribute_level=rules.RuleAttributeLevel.PERSON, attribute_name="POSTCODE"
            ),
            "SW19",
        ),
        # TARGET attribute level
        (
            [{"ATTRIBUTE_TYPE": "RSV", "LAST_SUCCESSFUL_DATE": "20240101"}],
            rule_builder.IterationRuleFactory.build(
                attribute_level=rules.RuleAttributeLevel.TARGET,
                attribute_name="LAST_SUCCESSFUL_DATE",
                attribute_target="RSV",
            ),
            "20240101",
        ),
        # COHORT attribute level
        (
            [{"ATTRIBUTE_TYPE": "COHORTS", "COHORT_LABEL": ""}],
            rule_builder.IterationRuleFactory.build(
                attribute_level=rules.RuleAttributeLevel.COHORT, attribute_name="COHORT_LABEL"
            ),
            "",
        ),
    ],
)
def test_get_attribute_value_for_all_attribute_levels(person_data: Row, rule: rules.IterationRule, expected: str):
    # Given
    calc = RuleCalculator(person_data=person_data, rule=rule)
    # When
    actual = calc.get_attribute_value()
    # Then
    assert actual == expected
