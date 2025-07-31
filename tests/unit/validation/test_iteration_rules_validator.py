from datetime import datetime

import pytest
from pydantic import ValidationError

from eligibility_signposting_api.config.contants import RULE_STOP_DEFAULT
from eligibility_signposting_api.model.campaign_config import RuleStop
from rules_validation_api.validators.iteration_validator import IterationValidation


class TestMandatoryFieldsSchemaValidations:
    def test_campaign_config_with_only_mandatory_fields_configuration(
            self, valid_iteration_rule_with_only_mandatory_fields
    ):
        try:
            IterationValidation(**(valid_iteration_rule_with_only_mandatory_fields["Iterations"][0]))
        except ValidationError as e:
            pytest.fail(f"Unexpected error during model instantiation: {e}")

    @pytest.mark.parametrize(
        "mandatory_field",
        [
            "Type"
            "Name"
            "Description"
            "Priority"
            "AttributeLevel"
            "Operator"
            "Comparator"
        ],
    )
    def test_missing_mandatory_fields(self, mandatory_field, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields["Iterations"][0].copy()
        data.pop(mandatory_field, None)  # Simulate missing field
        with pytest.raises(ValidationError):
            IterationValidation(**data)
        assert mandatory_field.lower()

    # Type
    def test_missing_type(self, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data.pop("Type", None)
        with pytest.raises(ValidationError) as e:
            IterationValidation(**data)
        assert any(err["loc"][-1] == "Type" for err in e.value.errors())

    # Name
    def test_missing_name(self, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data.pop("Name", None)
        with pytest.raises(ValidationError) as e:
            IterationValidation(**data)
        assert any(err["loc"][-1] == "Name" for err in e.value.errors())

    # Description
    def test_missing_description(self, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data.pop("Description", None)
        with pytest.raises(ValidationError) as e:
            IterationValidation(**data)
        assert any(err["loc"][-1] == "Description" for err in e.value.errors())

    # Priority
    def test_missing_priority(self, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data.pop("Priority", None)
        with pytest.raises(ValidationError) as e:
            IterationValidation(**data)
        assert any(err["loc"][-1] == "Priority" for err in e.value.errors())

    # AttributeLevel
    def test_missing_attribute_level(self, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data.pop("AttributeLevel", None)
        with pytest.raises(ValidationError) as e:
            IterationValidation(**data)
        assert any(err["loc"][-1] == "AttributeLevel" for err in e.value.errors())


class TestOptionalFieldsSchemaValidations:
    # AttributeName
    def test_attribute_name_accepts_value(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "AttributeName": "LAST_SUCCESSFUL_DATE"}
        model = IterationValidation(**data)
        assert model.attribute_name == "LAST_SUCCESSFUL_DATE"

    def test_attribute_name_accepts_none(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "AttributeName": None}
        model = IterationValidation(**data)
        assert model.attribute_name is None

    # CohortLabel
    def test_cohort_label_accepts_value(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "CohortLabel": "elid_all_people"}
        model = IterationValidation(**data)
        assert model.cohort_label == "elid_all_people"

    def test_cohort_label_accepts_none(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "CohortLabel": None}
        model = IterationValidation(**data)
        assert model.cohort_label is None

    # AttributeTarget
    def test_attribute_target_accepts_value(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "AttributeTarget": "RSV"}
        model = IterationValidation(**data)
        assert model.attribute_target == "RSV"

    def test_attribute_target_accepts_none(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "AttributeTarget": None}
        model = IterationValidation(**data)
        assert model.attribute_target is None

    # RuleStop
    def test_rule_stop_uses_default_when_missing(self, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data.pop("RuleStop", None)
        model = IterationValidation(**data)
        assert model.rule_stop == RuleStop(RULE_STOP_DEFAULT)

    def test_rule_stop_accepts_value(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "RuleStop": "soft_stop"}
        model = IterationValidation(**data)
        assert model.rule_stop == "soft_stop"

    # CommsRouting
    def test_comms_routing_accepts_value(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "CommsRouting": "RouteA"}
        model = IterationValidation(**data)
        assert model.comms_routing == "RouteA"

    def test_comms_routing_accepts_none(self, valid_iteration_rule_with_only_mandatory_fields):
        data = {**valid_iteration_rule_with_only_mandatory_fields, "CommsRouting": None}
        model = IterationValidation(**data)
        assert model.comms_routing is None
