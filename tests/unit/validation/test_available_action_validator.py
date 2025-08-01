import copy

import pytest
from pydantic import ValidationError

from rules_validation_api.validators.available_action_validator import AvailableActionValidation


# 🔍 Mandatory Fields
class TestMandatoryFieldsSchemaValidations:
    def test_valid_minimal_input(self, valid_available_action):
        data = copy.deepcopy(valid_available_action)
        data.pop("ActionDescription")
        data.pop("UrlLink")
        data.pop("UrlLabel")
        action = AvailableActionValidation(**data)
        assert action.action_type == "ButtonWithAuthLink"
        assert action.action_code == "BookNBS"
        assert action.action_description is None
        assert action.url_link is None
        assert action.url_label is None

    def test_missing_required_fields(self, valid_available_action):
        data = copy.deepcopy(valid_available_action)
        data.pop("ActionType")
        data.pop("ExternalRoutingCode")
        with pytest.raises(ValidationError) as exc_info:
            AvailableActionValidation(**data)
        error_msg = str(exc_info.value)
        assert "ActionType" in error_msg
        assert "ExternalRoutingCode" in error_msg


# 🔍 Optional Fields
class TestOptionalFieldsSchemaValidations:
    def test_valid_full_input(self, valid_available_action):
        action = AvailableActionValidation(**valid_available_action)
        assert action.action_type == "ButtonWithAuthLink"
        assert action.action_code == "BookNBS"
        assert action.action_description == ""
        assert str(action.url_link) == "http://www.nhs.uk/book-rsv"
        assert action.url_label == "Continue to booking"

    def test_empty_string_is_valid_for_optional_fields(self, valid_available_action):
        action = AvailableActionValidation(**valid_available_action)
        assert action.action_description == ""
        assert action.url_label == "Continue to booking"

    @pytest.mark.parametrize("bad_url", ["not-a-url", "ftp://bad", "123"])
    def test_invalid_url_raises_validation_error(self, valid_available_action, bad_url):
        data = copy.deepcopy(valid_available_action)
        data["UrlLink"] = bad_url
        with pytest.raises(ValidationError) as exc_info:
            AvailableActionValidation(**data)
        assert "UrlLink" in str(exc_info.value)
