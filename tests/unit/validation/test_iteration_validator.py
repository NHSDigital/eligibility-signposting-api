from datetime import datetime

import pytest
from pydantic import ValidationError

from rules_validation_api.validators.iteration_validator import IterationValidation


class TestMandatoryFieldsSchemaValidations:
    def test_campaign_config_with_only_mandatory_fields_configuration(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        try:
            IterationValidation(**(valid_campaign_config_with_only_mandatory_fields["Iterations"][0]))
        except ValidationError as e:
            pytest.fail(f"Unexpected error during model instantiation: {e}")

    @pytest.mark.parametrize(
        "mandatory_field",
        [
            "ID",
            "Version",
            "Name",
            "IterationDate",
            "Type",
            "DefaultCommsRouting",
            "DefaultNotEligibleRouting",
            "DefaultNotActionableRouting",
            "IterationCohorts",
            "IterationRules",
            "ActionsMapper",
        ],
    )
    def test_missing_mandatory_fields(self, mandatory_field, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields["Iterations"][0].copy()
        data.pop(mandatory_field, None)  # Simulate missing field
        with pytest.raises(ValidationError):
            IterationValidation(**data)
        assert mandatory_field.lower()

    # ID
    @pytest.mark.parametrize("id_value", ["ITER001", "X123", "IT01"])
    def test_valid_id(self, id_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0], "ID": id_value}
        model = IterationValidation(**data)
        assert model.id == id_value

    # Version
    @pytest.mark.parametrize("version_value", ["v1.0", "v2.3", "V4.5"])
    def test_valid_version(self, version_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0], "Version": version_value}
        model = IterationValidation(**data)
        assert model.version == version_value

    # Name
    @pytest.mark.parametrize("name_value", ["Mid-January Push", "Spring Surge", "Early Outreach"])
    def test_valid_name(self, name_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0], "Name": name_value}
        model = IterationValidation(**data)
        assert model.name == name_value

    # IterationDate
    @pytest.mark.parametrize("date_value", ["20250101", "20250215", "20250301"])
    def test_valid_iteration_date(self, date_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0], "IterationDate": date_value}
        model = IterationValidation(**data)
        expected_date = datetime.strptime(date_value, "%Y%m%d").date()
        assert model.iteration_date == expected_date, f"Expected {expected_date}, got {model.iteration_date}"

    # Type
    @pytest.mark.parametrize("type_value", ["A", "M", "S", "O"])
    def test_valid_type(self, type_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0], "Type": type_value}
        model = IterationValidation(**data)
        assert model.type == type_value

    @pytest.mark.parametrize("type_value", ["", "Z", None])
    def test_invalid_type(self, type_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0], "Type": type_value}
        with pytest.raises(ValidationError):
            IterationValidation(**data)

    # DefaultCommsRouting
    @pytest.mark.parametrize("routing_value", ["BOOK_NBS"])
    def test_valid_default_comms_routing(self, routing_value, valid_campaign_config_with_only_mandatory_fields):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultCommsRouting": routing_value,
        }
        model = IterationValidation(**data)
        assert model.default_comms_routing == routing_value

    # DefaultNotEligibleRouting
    @pytest.mark.parametrize("routing_value", ["RouteB", "NotEligComm", "NoComms"])
    def test_valid_default_not_eligible_routing(self, routing_value, valid_campaign_config_with_only_mandatory_fields):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotEligibleRouting": routing_value,
        }
        model = IterationValidation(**data)
        assert model.default_not_eligible_routing == routing_value

    # DefaultNotActionableRouting
    @pytest.mark.parametrize("routing_value", ["RouteC", "HoldComm", "Inactive"])
    def test_valid_default_not_actionable_routing(
        self, routing_value, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotActionableRouting": routing_value,
        }
        model = IterationValidation(**data)
        assert model.default_not_actionable_routing == routing_value


class TestOptionalFieldsSchemaValidations:
    @pytest.mark.parametrize("iteration_number", [1, 5, 10])
    def test_iteration_number(self, iteration_number, valid_campaign_config_with_only_mandatory_fields):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "IterationNumber": iteration_number,
        }
        model = IterationValidation(**data)
        assert model.iteration_number == iteration_number

    @pytest.mark.parametrize("approval_minimum", [0, 25, 99])
    def test_approval_minimum(self, approval_minimum, valid_campaign_config_with_only_mandatory_fields):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "ApprovalMinimum": approval_minimum,
        }
        model = IterationValidation(**data)
        assert model.approval_minimum == approval_minimum

    @pytest.mark.parametrize("approval_maximum", [100, 250, 999])
    def test_approval_maximum(self, approval_maximum, valid_campaign_config_with_only_mandatory_fields):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "ApprovalMaximum": approval_maximum,
        }
        model = IterationValidation(**data)
        assert model.approval_maximum == approval_maximum


class TestIterationCohortsSchemaValidations:
    def test_valid_iteration_if_actions_mapper_has_entry_for_the_provided_default_routing_key(self, valid_campaign_config_with_only_mandatory_fields):
        expected_action = {
            "ExternalRoutingCode": "BookLocal",
            "ActionDescription": "##Getting the vaccine\n"
                                 "You can get an RSV vaccination at your GP surgery.\n"
                                 "Your GP surgery may contact you about getting the RSV vaccine. "
                                 "This may be by letter, text, phone call, email or through the NHS App. "
                                 "You do not need to wait to be contacted before booking your vaccination.",
            "ActionType": "InfoText"
        }

        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
                "DefaultCommsRouting": "BOOK_LOCAL", "ActionsMapper": {
                "BOOK_LOCAL": expected_action
            }}
        IterationValidation(**data)

    def test_invalid_iteration_if_actions_mapper_has_no_entry_for_the_provided_default_routing_key(self, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
                "DefaultCommsRouting": "BOOK_LOCAL", "ActionsMapper": {}} # Missing BOOK_LOCAL in ActionsMapper

        with pytest.raises(ValidationError) as error:
            IterationValidation(**data)

        errors = error.value.errors()
        assert any(
            e["loc"][-1] == "actions_mapper" and "BOOK_LOCAL" in str(e["msg"])
            for e in errors
        ), "Expected validation error for missing BOOK_LOCAL entry in ActionsMapper"


