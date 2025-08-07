import pytest
from pydantic import ValidationError

from eligibility_signposting_api.model.campaign_config import AvailableAction
from rules_validation_api.validators.actions_mapper_validator import ActionsMapperValidator


@pytest.fixture
def valid_available_action():
    return {
        "ExternalRoutingCode": "BookNBS",
        "ActionDescription": "",
        "ActionType": "ButtonWithAuthLink",
        "UrlLink": "http://www.nhs.uk/book-rsv",
        "UrlLabel": "Continue to booking",
    }


class TestBUCValidations:
    def make_action(self, data: dict) -> AvailableAction:
        return AvailableAction(**data)

    def test_valid_actions_mapper(self, valid_available_action):
        data = {
            "action1": self.make_action(valid_available_action),
            "action2": self.make_action({**valid_available_action, "ExternalRoutingCode": "AltCode"}),
        }
        mapper = ActionsMapperValidator(root=data)

        expected_action_count = 2
        assert isinstance(mapper, ActionsMapperValidator)
        assert len(mapper.root) == expected_action_count

    @pytest.mark.parametrize(
        "invalid_action",
        [
            {"action1": ""},
            {"action1": "invalid_action"},
            {"action3": None},
            {"action1": "", "action3": None},
            {"action1": "invalid_action", "action2": ""},
        ],
    )
    def test_if_exception_raised_when_adding_invalid_actions_to_action_mapper(self, invalid_action):
        data = {"": invalid_action}
        with pytest.raises(ValidationError):
            ActionsMapperValidator(root=data)

    def test_invalid_actions_mapper_empty_key(self, valid_available_action):
        data = {"": self.make_action(valid_available_action), "action2": self.make_action(valid_available_action)}
        with pytest.raises(ValidationError) as exc_info:
            ActionsMapperValidator(root=data)
        assert "Invalid keys found in ActionsMapper" in str(exc_info.value)
        assert "['']" in str(exc_info.value)

    @pytest.mark.parametrize("bad_key", [""])
    def test_invalid_keys_parametrized(self, bad_key, valid_available_action):
        data = {
            bad_key: self.make_action(valid_available_action),
            "valid_key": self.make_action(valid_available_action),
        }
        with pytest.raises(ValidationError) as exc_info:
            ActionsMapperValidator(root=data)
        assert "Invalid keys found in ActionsMapper" in str(exc_info.value)
