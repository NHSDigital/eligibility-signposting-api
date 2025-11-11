from collections import Counter
from datetime import UTC, datetime
from typing import ClassVar

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
    @pytest.mark.parametrize("version_value", [1, 2, 100])
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
        expected_date = datetime.strptime(str(date_value), "%Y%m%d").replace(tzinfo=UTC).date()
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
            "ActionsMapper": {
                "BOOK_NBS": {
                    "ExternalRoutingCode": "BookNBS",
                    "ActionDescription": "",
                    "ActionType": "ButtonWithAuthLink",
                    "UrlLink": "http://www.nhs.uk/book-rsv",
                    "UrlLabel": "Continue to booking",
                }
            },
        }
        model = IterationValidation(**data)
        assert model.default_comms_routing == routing_value

    # DefaultNotEligibleRouting
    @pytest.mark.parametrize("routing_value", ["", "BOOK_NBS"])
    def test_valid_default_not_eligible_routing(self, routing_value, valid_campaign_config_with_only_mandatory_fields):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotEligibleRouting": routing_value,
            "ActionsMapper": {
                "BOOK_NBS": {
                    "ExternalRoutingCode": "BookNBS",
                    "ActionDescription": "",
                    "ActionType": "ButtonWithAuthLink",
                    "UrlLink": "http://www.nhs.uk/book-rsv",
                    "UrlLabel": "Continue to booking",
                }
            },
        }
        model = IterationValidation(**data)
        assert model.default_not_eligible_routing == routing_value

    # DefaultNotActionableRouting
    @pytest.mark.parametrize("routing_value", ["", "BOOK_NBS"])
    def test_valid_default_not_actionable_routing(
        self, routing_value, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotActionableRouting": routing_value,
            "ActionsMapper": {
                "BOOK_NBS": {
                    "ExternalRoutingCode": "BookNBS",
                    "ActionDescription": "",
                    "ActionType": "ButtonWithAuthLink",
                    "UrlLink": "http://www.nhs.uk/book-rsv",
                    "UrlLabel": "Continue to booking",
                }
            },
        }
        model = IterationValidation(**data)
        assert model.default_not_actionable_routing == routing_value

    def test_invalid_actions_mapper_empty_key(
        self, valid_campaign_config_with_only_mandatory_fields, valid_available_action
    ):
        actions_mapper = {"": valid_available_action, "action2": valid_available_action}
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "ActionsMapper": actions_mapper,
        }
        with pytest.raises(ValidationError):
            IterationValidation(**data)


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


class TestBUCValidations:
    book_local_1_action: ClassVar[dict] = {
        "ExternalRoutingCode": "BookLocal_1",
        "ActionDescription": "##Getting the vaccine\n"
        "You can get an RSV vaccination at your GP surgery.\n"
        "Your GP surgery may contact you about getting the RSV vaccine. "
        "This may be by letter, text, phone call, email or through the NHS App. "
        "You do not need to wait to be contacted before booking your vaccination.",
        "ActionType": "InfoText",
    }

    book_local_2_action: ClassVar[dict] = {
        "ExternalRoutingCode": "BookLocal_2",
        "ActionDescription": "##Getting the vaccine\n"
        "You can get an RSV vaccination at your GP surgery.\n"
        "Your GP surgery may contact you about getting the RSV vaccine. "
        "This may be by letter, text, phone call, email or through the NHS App. "
        "You do not need to wait to be contacted before booking your vaccination.",
        "ActionType": "InfoText",
    }

    def test_valid_iteration_if_actions_mapper_has_entry_for_the_provided_default_routing_key(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultCommsRouting": "BOOK_LOCAL_1|BOOK_LOCAL_2",
            "ActionsMapper": {"BOOK_LOCAL_1": self.book_local_1_action, "BOOK_LOCAL_2": self.book_local_2_action},
        }
        IterationValidation(**data)

    def test_invalid_iteration_if_actions_mapper_has_doesnt_have_entries_for_every_default_not_default_routing_keys(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultCommsRouting": "BOOK_LOCAL_1|BOOK_LOCAL_2",
            "ActionsMapper": {"BOOK_LOCAL_1": self.book_local_1_action},
        }
        with pytest.raises(ValidationError) as error:
            IterationValidation(**data)

        errors = error.value.errors()
        assert any(e["loc"][-1] == "actions_mapper" and "BOOK_LOCAL_2" in str(e["msg"]) for e in errors), (
            "Expected validation error for missing BOOK_LOCAL_2 entry in ActionsMapper"
        )

    def test_invalid_iteration_if_actions_mapper_has_no_entry_for_the_provided_default_routing_key(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultCommsRouting": "BOOK_LOCAL",
            "ActionsMapper": {},
        }  # Missing BOOK_LOCAL in ActionsMapper

        with pytest.raises(ValidationError) as error:
            IterationValidation(**data)

        errors = error.value.errors()
        assert any(e["loc"][-1] == "actions_mapper" and "BOOK_LOCAL" in str(e["msg"]) for e in errors), (
            "Expected validation error for missing BOOK_LOCAL entry in ActionsMapper"
        )

    def test_valid_iteration_if_actions_mapper_has_entry_for_the_provided_default_not_eligible_routing_key(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotEligibleRouting": "BOOK_LOCAL_1|BOOK_LOCAL_2",
            "ActionsMapper": {"BOOK_LOCAL_1": self.book_local_1_action, "BOOK_LOCAL_2": self.book_local_2_action},
        }
        IterationValidation(**data)

    def test_invalid_iteration_if_actions_mapper_has_doesnt_have_entries_for_every_default_not_eligible_routing_keys(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotEligibleRouting": "BOOK_LOCAL_1|BOOK_LOCAL_2",
            "ActionsMapper": {"BOOK_LOCAL_1": self.book_local_1_action},
        }
        with pytest.raises(ValidationError) as error:
            IterationValidation(**data)

        errors = error.value.errors()
        assert any(e["loc"][-1] == "actions_mapper" and "BOOK_LOCAL_2" in str(e["msg"]) for e in errors), (
            "Expected validation error for missing BOOK_LOCAL_2 entry in ActionsMapper"
        )

    def test_invalid_iteration_if_actions_mapper_has_no_entry_for_the_provided_default_not_eligible_routing(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotEligibleRouting": "BOOK_LOCAL",
            "ActionsMapper": {},
        }  # Missing BOOK_LOCAL in ActionsMapper

        with pytest.raises(ValidationError) as error:
            IterationValidation(**data)

        errors = error.value.errors()
        assert any(e["loc"][-1] == "actions_mapper" and "BOOK_LOCAL" in str(e["msg"]) for e in errors), (
            "Expected validation error for missing BOOK_LOCAL entry in ActionsMapper"
        )

    def test_valid_iteration_if_actions_mapper_has_entry_for_the_provided_default_not_actionable_routing_key(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotActionableRouting": "BOOK_LOCAL_1|BOOK_LOCAL_2",
            "ActionsMapper": {"BOOK_LOCAL_1": self.book_local_1_action, "BOOK_LOCAL_2": self.book_local_2_action},
        }
        IterationValidation(**data)

    def test_invalid_iteration_if_actions_mapper_has_doesnt_have_entries_for_every_default_not_actionable_routing_keys(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotActionableRouting": "BOOK_LOCAL_1|BOOK_LOCAL_2",
            "ActionsMapper": {"BOOK_LOCAL_1": self.book_local_1_action},
        }
        with pytest.raises(ValidationError) as error:
            IterationValidation(**data)

        errors = error.value.errors()
        assert any(e["loc"][-1] == "actions_mapper" and "BOOK_LOCAL_2" in str(e["msg"]) for e in errors), (
            "Expected validation error for missing BOOK_LOCAL_2 entry in ActionsMapper"
        )

    def test_invalid_iteration_if_actions_mapper_has_no_entry_for_the_provided_default_not_actionable_routing(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "DefaultNotActionableRouting": "BOOK_LOCAL",
            "ActionsMapper": {},
        }  # Missing BOOK_LOCAL in ActionsMapper

        with pytest.raises(ValidationError) as error:
            IterationValidation(**data)

        errors = error.value.errors()
        assert any(e["loc"][-1] == "actions_mapper" and "BOOK_LOCAL" in str(e["msg"]) for e in errors), (
            "Expected validation error for missing BOOK_LOCAL entry in ActionsMapper"
        )

    @pytest.mark.parametrize("rule_type", ["R", "X", "Y", "F"])
    @pytest.mark.parametrize(
        ("default_routing", "actions_mapper"),
        [
            ("BOOK_LOCAL_1|BOOK_LOCAL_2", {"BOOK_LOCAL_1": book_local_1_action, "BOOK_LOCAL_2": book_local_2_action}),
            ("BOOK_LOCAL_1", {"BOOK_LOCAL_1": book_local_1_action}),
            ("", {"BOOK_LOCAL_1": book_local_1_action}),
        ],
    )
    def test_valid_iteration_if_actions_mapper_exists_for_rule_routing(
        self, valid_campaign_config_with_only_mandatory_fields, rule_type, default_routing, actions_mapper
    ):
        iteration_rule = {
            "Type": rule_type,
            "Name": "Test Rule",
            "Description": "Test rule description",
            "Operator": "is_empty",
            "Comparator": "",
            "AttributeTarget": "RSV",
            "AttributeLevel": "TARGET",
            "AttributeName": "LAST_SUCCESSFUL_DATE",
            "Priority": 100,
            "CommsRouting": default_routing,
        }

        iteration_data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "IterationRules": [iteration_rule],
            "ActionsMapper": actions_mapper,
        }

        iteration = IterationValidation(**iteration_data)
        assert iteration is not None, (
            f"Expected iteration to be valid for rule type '{rule_type}' with routing '{default_routing}'"
        )

    @pytest.mark.parametrize("rule_type", ["R", "X", "Y"])
    @pytest.mark.parametrize(
        ("default_routing", "actions_mapper"),
        [
            ("BOOK_LOCAL_1|BOOK_LOCAL_2", {"BOOK_LOCAL_2": book_local_2_action}),
            ("BOOK_LOCAL_1", {"BOOK_LOCAL_2": book_local_2_action}),
        ],
    )
    def test_invalid_iteration_if_actions_mapper_exists_for_rule_routing(
        self, valid_campaign_config_with_only_mandatory_fields, rule_type, default_routing, actions_mapper
    ):
        iteration_rule = {
            "Type": rule_type,
            "Name": "Test Rule",
            "Description": "Test rule description",
            "Operator": "is_empty",
            "Comparator": "",
            "AttributeTarget": "RSV",
            "AttributeLevel": "TARGET",
            "AttributeName": "LAST_SUCCESSFUL_DATE",

            "Priority": 100,
            "CommsRouting": default_routing,
        }

        iteration_data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "IterationRules": [iteration_rule],
            "ActionsMapper": actions_mapper,
        }

        with pytest.raises(ValidationError) as error:
            IterationValidation(**iteration_data)

        errors = error.value.errors()
        assert any(e["loc"][-1] == "iteration_rules" and "BOOK_LOCAL_1" in str(e["msg"]) for e in errors), (
            "Expected validation error for missing BOOK_LOCAL entry in ActionsMapper"
        )

    def test_invalid_iteration_if_more_than_one_cohort_has_the_same_cohort_label(
        self, valid_campaign_config_with_only_mandatory_fields, valid_iteration_cohorts
    ):
        iteration_data = {
            **valid_campaign_config_with_only_mandatory_fields["Iterations"][0],
            "IterationCohorts": [
                valid_iteration_cohorts(label="label_1", group="group_1"),
                valid_iteration_cohorts(label="label_1", group="group_1"),
                valid_iteration_cohorts(label="label_1", group="group_1"),
                valid_iteration_cohorts(label="label_1", group="group_2"),
                valid_iteration_cohorts(label="label_2", group="group_1"),
                valid_iteration_cohorts(label="label_2", group="group_2"),
            ],
        }

        with pytest.raises(ValidationError) as error:
            IterationValidation(**iteration_data)

        errors = error.value.errors()
        # Extract all cohort_label mentions from error inputs
        label_mentions = [err["input"] for err in errors if err.get("ctx")]

        # Count occurrences
        label_counts = Counter(label_mentions)

        # Assert expected counts
        expected_label_1_error_count = 3
        expected_label_2_error_count = 1

        assert label_counts["label_1"] == expected_label_1_error_count, (
            f"Expected {expected_label_1_error_count} errors for label_1, got {label_counts['label_1']}"
        )
        assert label_counts["label_2"] == expected_label_2_error_count, (
            f"Expected {expected_label_2_error_count} error for label_2, got {label_counts['label_2']}"
        )
