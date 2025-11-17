import pytest
from pydantic_core._pydantic_core import ValidationError

from rules_validation_api.validators.rule_entry_validator import RuleEntryValidation


class TestRuleEntryValidator:

    @pytest.mark.parametrize("rule_text_value", ["", "A rule description", "Sample text", "### Header"])
    def test_valid_rule_text(self, rule_text_value):
        data = {"RuleNames": ["Already Vaccinated"],
                "RuleCode": "Already Jabbed",
                "RuleText": rule_text_value,
                "Description": "description"}
        result = RuleEntryValidation(**data)
        assert result.rule_text == rule_text_value


    @pytest.mark.parametrize("rule_text_value", ["###Header"])
    def test_invalid_rule_text(self, rule_text_value):
        data = {"RuleNames": ["Already Vaccinated"],
                "RuleCode": "Already Jabbed",
                "RuleText": rule_text_value,
                "Description": "description"}
        with pytest.raises(ValidationError):
            RuleEntryValidation(**data)

