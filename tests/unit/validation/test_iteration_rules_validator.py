import pytest
from pydantic import ValidationError

from eligibility_signposting_api.model.campaign_config import RuleAttributeLevel
from rules_validation_api.validators.iteration_validator import IterationRuleValidation


class TestMandatoryFieldsSchemaValidations:
    def test_campaign_config_with_only_mandatory_fields_configuration(
        self, valid_iteration_rule_with_only_mandatory_fields
    ):
        try:
            IterationRuleValidation(**valid_iteration_rule_with_only_mandatory_fields)
        except ValidationError as e:
            pytest.fail(f"Unexpected error during model instantiation: {e}")

    @pytest.mark.parametrize(
        "mandatory_field",
        ["Type", "Name", "Description", "Priority", "AttributeLevel", "Operator", "Comparator"],
    )
    def test_missing_mandatory_fields(self, mandatory_field, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data.pop(mandatory_field, None)  # Simulate missing field
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)
        assert mandatory_field.lower()

    @pytest.mark.parametrize("type_value", ["F", "S", "R", "X", "Y"])
    def test_valid_type(self, type_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Type"] = type_value
        result = IterationRuleValidation(**data)
        assert result.type.value == type_value

    @pytest.mark.parametrize("type_value", ["Z", 123, None])
    def test_invalid_type(self, type_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Type"] = type_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    @pytest.mark.parametrize("name_value", ["", "ValidName", "Test_Rule_01"])
    def test_valid_name(self, name_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Name"] = name_value
        result = IterationRuleValidation(**data)
        assert result.name == name_value

    @pytest.mark.parametrize("name_value", [None, 42])
    def test_invalid_name(self, name_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Name"] = name_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    @pytest.mark.parametrize("description_value", ["", "A rule description", "Sample text"])
    def test_valid_description(self, description_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Description"] = description_value
        result = IterationRuleValidation(**data)
        assert result.description == description_value

    @pytest.mark.parametrize("description_value", [None])
    def test_invalid_description(self, description_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Description"] = description_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    @pytest.mark.parametrize("priority_value", [-1, -5, 1, 100, 999])
    def test_valid_priority(self, priority_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Priority"] = priority_value
        result = IterationRuleValidation(**data)
        assert result.priority == priority_value

    @pytest.mark.parametrize("priority_value", ["high", None])
    def test_invalid_priority(self, priority_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Priority"] = priority_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    @pytest.mark.parametrize("attribute_level", ["PERSON", "TARGET"])
    def test_valid_attribute_level_person_and_targer(
        self, attribute_level, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeLevel"] = attribute_level
        data["AttributeName"] = "Something"  # Ignoring the validation constraint btw AttributeLevel and AttributeName
        result = IterationRuleValidation(**data)
        assert result.attribute_level == attribute_level

    @pytest.mark.parametrize("attribute_level", ["COHORT"])
    def test_valid_attribute_level_cohort(self, attribute_level, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeLevel"] = attribute_level
        data["AttributeName"] = None  # Ignoring the validation constraint btw AttributeLevel and AttributeName
        result = IterationRuleValidation(**data)
        assert result.attribute_level == attribute_level

    @pytest.mark.parametrize("attribute_level", ["", None, 42, "basic", "BASIC"])
    def test_invalid_attribute_level(self, attribute_level, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeLevel"] = attribute_level
        data["AttributeName"] = None  # Ignoring the validation constraint btw AttributeLevel and AttributeName
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    @pytest.mark.parametrize("operator_value", ["=", "!=", ">", "<=", "contains", "is_true"])
    def test_valid_operator(self, operator_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Operator"] = operator_value
        result = IterationRuleValidation(**data)
        assert result.operator.value == operator_value

    @pytest.mark.parametrize("operator_value", ["approx", "", None])
    def test_invalid_operator(self, operator_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Operator"] = operator_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    @pytest.mark.parametrize("comparator_value", ["status", "true", "0"])
    def test_valid_comparator(self, comparator_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Comparator"] = comparator_value
        result = IterationRuleValidation(**data)
        assert result.comparator == comparator_value

    @pytest.mark.parametrize("comparator_value", [None, 123])
    def test_invalid_comparator(self, comparator_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Comparator"] = comparator_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    @pytest.mark.parametrize(
        ("rule_stop_input", "expected_bool"),
        [
            (True, True),
            (False, False),
            ("Y", True),
            ("N", False),
            ("YES", False),
            ("NO", False),
            ("YEAH", False),
            ("ONE", False),
        ],
    )
    def test_rule_stop_boolean_resolution(
        self, rule_stop_input, expected_bool, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["RuleStop"] = rule_stop_input
        result = IterationRuleValidation(**data)
        assert result.rule_stop is expected_bool


class TestOptionalFieldsSchemaValidations:
    # AttributeName
    @pytest.mark.parametrize("attr_name", ["status", "user_type"])
    def test_valid_attribute_name(self, attr_name, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeName"] = attr_name
        result = IterationRuleValidation(**data)
        assert result.attribute_name == attr_name

    @pytest.mark.parametrize("attr_name", [123, {}, []])
    def test_invalid_attribute_name(self, attr_name, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeName"] = attr_name
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    # CohortLabel
    @pytest.mark.parametrize(
        ("label", "expected_parsed_cohort_label"),
        [
            ("Cohort_A", ["Cohort_A"]),
            ("Cohort_A,Cohort_B", ["Cohort_A", "Cohort_B"]),
            ("Cohort_C,,,,", ["Cohort_C"]),
            ("Cohort_D,,,,Cohort_E", ["Cohort_D", "Cohort_E"]),
            (",,,,Cohort_E,,,,", ["Cohort_E"]),
            (",,,,", []),
            ("", []),
            (None, []),
        ],
    )
    def test_cohort_label_parsing(
        self, label, expected_parsed_cohort_label, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["CohortLabel"] = label
        result = IterationRuleValidation(**data)
        assert result.parsed_cohort_labels == expected_parsed_cohort_label

    @pytest.mark.parametrize("label", [123, [], {}])
    def test_invalid_cohort_label(self, label, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["CohortLabel"] = label
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    # AttributeTarget
    @pytest.mark.parametrize("target", ["RSV", "COVID"])
    def test_valid_attribute_target(self, target, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeTarget"] = target
        result = IterationRuleValidation(**data)
        assert result.attribute_target == target

    @pytest.mark.parametrize("target", [123, [], {}, "RSV1"])
    def test_invalid_attribute_target(self, target, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeTarget"] = target
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    # RuleStop
    @pytest.mark.parametrize("rule_stop_value", [True, False, "Y", "N", "YES", "NO", "YEAH", "ONE"])
    def test_valid_rule_stop(self, rule_stop_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["RuleStop"] = rule_stop_value
        result = IterationRuleValidation(**data)
        assert isinstance(result.rule_stop, bool)

    @pytest.mark.parametrize("rule_stop_value", [{}, None])
    def test_invalid_rule_stop(self, rule_stop_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["RuleStop"] = rule_stop_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)

    # CommsRouting
    @pytest.mark.parametrize("routing_value", ["route_A", None])
    def test_valid_comms_routing(self, routing_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["CommsRouting"] = routing_value
        result = IterationRuleValidation(**data)
        assert result.comms_routing == routing_value

    @pytest.mark.parametrize("routing_value", [123, [], {}])
    def test_invalid_comms_routing(self, routing_value, valid_iteration_rule_with_only_mandatory_fields):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["CommsRouting"] = routing_value
        with pytest.raises(ValidationError):
            IterationRuleValidation(**data)


class TestBUCValidations:
    @pytest.mark.parametrize("attribute_name", [None, "", "COHORT_LABEL"])
    def test_valid_when_attribute_level_is_cohort_then_attribute_name_should_be_none_or_cohort_label(
        self, attribute_name, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeLevel"] = "COHORT"
        data["AttributeName"] = attribute_name
        result = IterationRuleValidation(**data)
        assert result.attribute_name == attribute_name

    @pytest.mark.parametrize("attribute_name", ["LAST_SUCCESSFUL_DATE", "cohort_label"])
    def test_invalid_when_attribute_level_is_cohort_but_attribute_name_is_neither_none_nor_cohort_label(
        self, attribute_name, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeLevel"] = "COHORT"
        data["AttributeName"] = attribute_name
        with pytest.raises(ValidationError) as error:
            IterationRuleValidation(**data)
        msg = "When attribute_level is COHORT, attribute_name must be COHORT_LABEL or None (default:COHORT_LABEL)"
        assert msg in str(error.value)

    @pytest.mark.parametrize("rule_type", ["F", "S"])
    def test_valid_when_cohort_label_present_for_type_f_or_s(
        self, rule_type, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Type"] = rule_type
        data["CohortLabel"] = "Test Cohort"
        result = IterationRuleValidation(**data)
        assert result.cohort_label == "Test Cohort"

    @pytest.mark.parametrize("rule_type", ["R", "X", "Y"])
    def test_invalid_when_cohort_label_present_for_non_f_s_types(
        self, rule_type, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Type"] = rule_type
        data["CohortLabel"] = "Invalid Cohort"
        with pytest.raises(ValidationError) as error:
            IterationRuleValidation(**data)
        msg = "CohortLabel is only allowed for rule types F and S."
        assert msg in str(error.value)

    @pytest.mark.parametrize("rule_type", ["R", "X", "Y"])
    def test_valid_when_cohort_label_absent_for_non_f_s_types(
        self, rule_type, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["Type"] = rule_type
        data.pop("CohortLabel", None)
        result = IterationRuleValidation(**data)
        assert result.cohort_label is None

    @pytest.mark.parametrize(
        ("attribute_level", "attribute_name", "is_valid"),
        [
            (RuleAttributeLevel.COHORT, None, True),  # Allowed: name optional for cohort
            (RuleAttributeLevel.COHORT, "COHORT_LABEL", True),  # Allowed: name provided
            (RuleAttributeLevel.TARGET, "RSV", True),  # Allowed: name provided for target
            (RuleAttributeLevel.TARGET, None, False),  # NOT allowed: missing for non-cohort
        ],
    )
    def test_attribute_name_optional_only_for_cohort(
        self, attribute_level, attribute_name, is_valid, valid_iteration_rule_with_only_mandatory_fields
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeLevel"] = attribute_level
        data["AttributeName"] = attribute_name

        if is_valid:
            # Should validate with no exceptions
            IterationRuleValidation(**data)
        else:
            with pytest.raises(ValidationError) as exc:
                IterationRuleValidation(**data)

            assert "AttributeName must be set" in str(exc.value)

    @pytest.mark.parametrize(
        ("attribute_level", "attribute_target", "attribute_name", "is_valid"),
        [
            (RuleAttributeLevel.TARGET, "RSV", "BOOKED_APPOINTMENT_DATE", True),  # Valid: required for TARGET
            (RuleAttributeLevel.TARGET, None, "BOOKED_APPOINTMENT_DATE", False),  # Invalid: missing
            (RuleAttributeLevel.COHORT, None, "COHORT_LABEL", True),  # Valid: not required
        ],
    )
    def test_attribute_target_mandatory_for_target_level(
        self,
        attribute_level,
        attribute_target,
        attribute_name,
        is_valid,
        valid_iteration_rule_with_only_mandatory_fields,
    ):
        data = valid_iteration_rule_with_only_mandatory_fields.copy()
        data["AttributeLevel"] = attribute_level
        data["AttributeTarget"] = attribute_target
        data["AttributeName"] = attribute_name

        if is_valid:
            IterationRuleValidation(**data)
        else:
            with pytest.raises(ValidationError) as exc:
                IterationRuleValidation(**data)

            assert "AttributeTarget is mandatory" in str(exc.value)
