import pytest
from pydantic import ValidationError

from rules_validation_api.validators.rules_validator import RulesValidation


def test_valid_campaign_config(valid_campaign_config_with_only_mandatory_fields):
    config_data = {"campaign_config": valid_campaign_config_with_only_mandatory_fields}
    validated = RulesValidation(**config_data)
    assert validated.campaign_config.name is not None


def test_invalid_campaign_config_missing_field():
    invalid_data = {}

    with pytest.raises(ValidationError):
        RulesValidation(**invalid_data)
