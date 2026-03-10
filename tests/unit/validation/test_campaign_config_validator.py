from datetime import datetime

import pytest
from freezegun import freeze_time
from pydantic import ValidationError

from rules_validation_api.validators.campaign_config_validator import CampaignConfigValidation


class TestMandatoryFieldsSchemaValidations:
    def test_campaign_config_with_only_mandatory_fields_configuration(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        try:
            CampaignConfigValidation(**valid_campaign_config_with_only_mandatory_fields)
        except ValidationError as e:
            pytest.fail(f"Unexpected error during model instantiation: {e}")

    @pytest.mark.parametrize(
        "mandatory_field",
        [
            "ID",
            "Version",
            "Name",
            "Type",
            "Target",
            "IterationFrequency",
            "IterationType",
            "StartDate",
            "EndDate",
            "Iterations",
        ],
    )
    def test_missing_mandatory_fields(self, mandatory_field, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data.pop(mandatory_field, None)  # Simulate missing field
        with pytest.raises(ValidationError):
            CampaignConfigValidation(**data)

    # ID
    @pytest.mark.parametrize("id_value", ["CAMP001", "12345", "X001"])
    def test_valid_id(self, id_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "ID": id_value}
        model = CampaignConfigValidation(**data)
        assert model.id == id_value

    # Version
    @pytest.mark.parametrize("version_value", [1, 2, 100])
    def test_valid_version(self, version_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Version": version_value}
        model = CampaignConfigValidation(**data)
        assert model.version == version_value

    # Name
    @pytest.mark.parametrize("name_value", ["Spring Campaign", "COVID-Alert", "Mass Outreach"])
    def test_valid_name(self, name_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Name": name_value}
        model = CampaignConfigValidation(**data)
        assert model.name == name_value

    # Type
    @pytest.mark.parametrize("type_value", ["V", "S"])
    def test_valid_type(self, type_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Type": type_value}
        model = CampaignConfigValidation(**data)
        assert model.type == type_value

    @pytest.mark.parametrize("type_value", ["X", "", None])
    def test_invalid_type(self, type_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Type": type_value}
        with pytest.raises(ValidationError):
            CampaignConfigValidation(**data)

    # Target
    @pytest.mark.parametrize("target_value", ["COVID", "FLU", "MMR", "RSV"])
    def test_valid_target(self, target_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Target": target_value}
        model = CampaignConfigValidation(**data)
        assert model.target == target_value

    @pytest.mark.parametrize("target_value", ["XYZ", "ABC", "", None])
    def test_invalid_target(self, target_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Target": target_value}
        with pytest.raises(ValidationError):
            CampaignConfigValidation(**data)

    # IterationFrequency
    @pytest.mark.parametrize("freq_value", ["X", "D", "W", "M", "Q", "A"])
    def test_valid_iteration_frequency(self, freq_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "IterationFrequency": freq_value}
        model = CampaignConfigValidation(**data)
        assert model.iteration_frequency == freq_value

    @pytest.mark.parametrize("freq_value", ["Z", "", None])
    def test_invalid_iteration_frequency(self, freq_value, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "IterationFrequency": freq_value}
        with pytest.raises(ValidationError):
            CampaignConfigValidation(**data)

    # IterationType
    @pytest.mark.parametrize("iter_type", ["A", "M", "S", "O"])
    def test_valid_iteration_type(self, iter_type, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "IterationType": iter_type}
        model = CampaignConfigValidation(**data)
        assert model.iteration_type == iter_type

    @pytest.mark.parametrize("iter_type", ["B", "", None])
    def test_invalid_iteration_type(self, iter_type, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "IterationType": iter_type}
        with pytest.raises(ValidationError):
            CampaignConfigValidation(**data)

    # StartDate
    @pytest.mark.parametrize(
        "start_date",
        [
            "",  # empty string
            "invalid-date",  # malformed value
        ],
    )
    def test_invalid_start_date(self, start_date, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = start_date

        with pytest.raises(ValidationError) as exc_info:
            CampaignConfigValidation(**data)

        errors = exc_info.value.errors()
        for error in errors:
            assert error["loc"][0] == "StartDate"

    # EndDates
    @pytest.mark.parametrize(
        "end_date",
        [
            "",  # empty string
            "31032025",  # malformed value
        ],
    )
    def test_invalid_end_date(self, end_date, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["EndDate"] = end_date

        with pytest.raises(ValidationError) as exc_info:
            CampaignConfigValidation(**data)

        errors = exc_info.value.errors()
        for error in errors:
            assert error["loc"][0] == "EndDate"


class TestOptionalFieldsSchemaValidations:
    @pytest.mark.parametrize("manager", [["alice"], ["bob"], ["carol"]])
    def test_manager_field(self, manager, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Manager": manager}
        model = CampaignConfigValidation(**data)
        assert model.manager == manager

    @pytest.mark.parametrize("approver", [["alice"], ["bob"], ["carol"]])
    def test_approver_field(self, approver, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Approver": approver}
        model = CampaignConfigValidation(**data)
        assert model.approver == approver

    @pytest.mark.parametrize("reviewer", [["alice"], ["bob"], ["carol"]])
    def test_reviewer_field(self, reviewer, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Reviewer": reviewer}
        model = CampaignConfigValidation(**data)
        assert model.reviewer == reviewer

    @pytest.mark.parametrize("iteration_time", ["14:00:00", "09:30:00", "18:45:00"])
    def test_iteration_time_field(self, iteration_time, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "IterationTime": iteration_time}
        model = CampaignConfigValidation(**data)
        assert model.iteration_time == datetime.strptime(iteration_time, "%H:%M:%S").time()  # noqa: DTZ007

    @pytest.mark.parametrize("routing", ["email", "sms", "push"])
    def test_default_comms_routing_field(self, routing, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "DefaultCommsRouting": routing}
        model = CampaignConfigValidation(**data)
        assert model.default_comms_routing == routing

    @pytest.mark.parametrize("min_approval", [0, 1, 2])
    def test_approval_minimum_field(self, min_approval, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "ApprovalMinimum": min_approval}
        model = CampaignConfigValidation(**data)
        assert model.approval_minimum == min_approval

    @pytest.mark.parametrize("max_approval", [5, 10, 15])
    def test_approval_maximum_field(self, max_approval, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "ApprovalMaximum": max_approval}
        model = CampaignConfigValidation(**data)
        assert model.approval_maximum == max_approval


class TestBUCValidations:
    # StartDate and EndDates
    @pytest.mark.parametrize(
        ("start_date", "end_date"),
        [
            ("20250101", "20250331"),  # valid range
            ("20250201", "20250228"),  # valid short range
        ],
    )
    def test_valid_start_and_end_dates_and_iteration_dates_relation(
        self, start_date, end_date, valid_campaign_config_with_only_mandatory_fields
    ):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = start_date
        data["EndDate"] = end_date
        data["Iterations"][0]["IterationDate"] = "20250202"
        data["Iterations"][1]["IterationDate"] = "20250203"
        CampaignConfigValidation(**data)

    # StartDate and EndDates
    @pytest.mark.parametrize(
        ("start_date", "end_date"),
        [
            ("20250202", "20250202"),  # same day
        ],
    )
    def test_valid_start_and_end_dates_and_iteration_dates_relation_for_a_one_day_campaign(
        self, start_date, end_date, valid_campaign_config_with_only_mandatory_fields
    ):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = start_date
        data["EndDate"] = end_date
        data["Iterations"][0]["IterationDate"] = "20250202"
        data["Iterations"].pop(1)
        CampaignConfigValidation(**data)

    @pytest.mark.parametrize(
        ("start_date", "end_date"),
        [
            ("20240729", "20241228"),  # Campaign ends date is before the iteration date
        ],
    )
    def test_invalid_end_dates_and_iteration_dates_relation(
        self, start_date, end_date, valid_campaign_config_with_only_mandatory_fields
    ):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = start_date
        data["EndDate"] = end_date
        data["Iterations"][0]["IterationDate"] = "20241229"
        data["Iterations"][1]["IterationDate"] = "20241230"
        with pytest.raises(ValidationError) as exc_info:
            CampaignConfigValidation(**data)

        errors = exc_info.value.errors()
        assert "Starts after" in errors[0]["msg"]
        assert "Starts after" in errors[0]["msg"]

    @pytest.mark.parametrize(
        ("start_date", "end_date"),
        [
            ("20241230", "20250101"),  # Campaign start date is after the iteration date
        ],
    )
    def test_invalid_start_date_and_iteration_dates_relation(
        self, start_date, end_date, valid_campaign_config_with_only_mandatory_fields
    ):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = start_date
        data["EndDate"] = end_date
        data["Iterations"][0]["IterationDate"] = "20241229"
        data["Iterations"][1]["IterationDate"] = "20241228"
        with pytest.raises(ValidationError) as exc_info:
            CampaignConfigValidation(**data)

        errors = exc_info.value.errors()
        assert "Starts before" in errors[0]["msg"]
        assert "Starts before" in errors[0]["msg"]

    # Iteration
    def test_validate_iterations_non_empty(self, valid_campaign_config_with_only_mandatory_fields):
        data = {**valid_campaign_config_with_only_mandatory_fields, "Iterations": []}
        with pytest.raises(ValidationError) as error:
            CampaignConfigValidation(**data)
        errors = error.value.errors()
        assert any(e["loc"][-1] == "Iterations" for e in errors), "Expected validation error on 'Iterations'"

    def test_unique_iteration_ids(
        self, valid_campaign_config_with_only_mandatory_fields, valid_iteration_with_only_mandatory_fields
    ):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["Iterations"].append(valid_iteration_with_only_mandatory_fields.copy())
        data["Iterations"][1]["ID"] = data["Iterations"][0]["ID"]
        with pytest.raises(ValidationError) as exc_info:
            CampaignConfigValidation(**data)

        # Extract the error message
        error_message = str(exc_info.value)

        # Assert that the duplicate ID appears in the message
        duplicate_id = data["Iterations"][0]["ID"]
        assert f"Iterations contain duplicate IDs: {duplicate_id}" in error_message

    def test_error_approval_minimum_is_greater_than_approval_maximum(
        self, valid_campaign_config_with_only_mandatory_fields
    ):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["ApprovalMinimum"] = 2
        data["ApprovalMaximum"] = 1
        with pytest.raises(ValidationError):
            CampaignConfigValidation(**data)

    @pytest.mark.parametrize(
        ("approval_min", "approval_max"),
        [
            (1, 2),
            (1, 1),
        ],
    )
    def test_approval_minimum_greater_than_approval_maximum_is_invalid(
        self,
        valid_campaign_config_with_only_mandatory_fields,
        approval_min,
        approval_max,
    ):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["ApprovalMinimum"] = approval_min
        data["ApprovalMaximum"] = approval_max
        CampaignConfigValidation(**data)

    @freeze_time("2026-06-01 00:05:00")  # BST
    def test_campaign_live_during_bst_transition(self, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        # Align Campaign Dates
        data["StartDate"] = "20260601"
        data["EndDate"] = "20260630"

        # Fix Iterations to be within June 2026
        for i, iteration in enumerate(data["Iterations"]):
            iteration["IterationDate"] = f"202606{10 + i}"

        model = CampaignConfigValidation(**data)
        assert model.campaign_live is True

    @freeze_time("2026-01-01 00:05:00")  # GMT
    def test_campaign_live_during_gmt(self, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = "20260101"
        data["EndDate"] = "20260131"

        for i, iteration in enumerate(data["Iterations"]):
            iteration["IterationDate"] = f"202601{10 + i}"

        model = CampaignConfigValidation(**data)
        assert model.campaign_live is True

    def test_iteration_datetime_utc_conversion(self, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["IterationTime"] = "09:00:00"

        # Test Summer (BST) - Ensure Campaign covers July
        data["StartDate"] = "20260701"
        data["EndDate"] = "20260731"
        data["Iterations"] = [data["Iterations"][0]]  # Simplify to 1 iteration for this test
        data["Iterations"][0]["IterationDate"] = "20260701"

        model_summer = CampaignConfigValidation(**data)
        assert model_summer.iterations[0].iteration_datetime_utc.hour == 8  # noqa : PLR2004

        # Test Winter (GMT) - Ensure Campaign covers January
        data["StartDate"] = "20260101"
        data["EndDate"] = "20260131"
        data["Iterations"][0]["IterationDate"] = "20260101"

        model_winter = CampaignConfigValidation(**data)
        assert model_winter.iterations[0].iteration_datetime_utc.hour == 9  # noqa : PLR2004

    @freeze_time("2026-05-31 22:59:59")  # 1 second before BST Midnight
    def test_campaign_not_live_yet_bst(self, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = "20260601"
        data["EndDate"] = "20260630"

        for i, iteration in enumerate(data["Iterations"]):
            iteration["IterationDate"] = f"202606{10 + i}"

        model = CampaignConfigValidation(**data)
        assert model.campaign_live is False

    @freeze_time("2026-03-29 00:59:59")  # 1 second before BST Midnight
    def test_get_current_iteration_1sec_before_bst(self, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = "20260301"
        data["EndDate"] = "20260630"
        iteration = data["Iterations"][0]
        iteration["IterationDate"] = "20260329"
        iteration["IterationTime"] = "01:00:00"
        iteration = data["Iterations"][1]
        iteration["IterationDate"] = "20260331"

        model = CampaignConfigValidation(**data)

        with pytest.raises(StopIteration):
            assert model.current_iteration

    @freeze_time("2026-03-29 01:00:00")  # Just after bst
    def test_get_current_iteration_just_after_bst(self, valid_campaign_config_with_only_mandatory_fields):
        data = valid_campaign_config_with_only_mandatory_fields.copy()
        data["StartDate"] = "20260301"
        data["EndDate"] = "20260630"
        iteration = data["Iterations"][0]
        iteration["IterationDate"] = "20260329"
        iteration["IterationTime"] = "01:00:00"
        iteration = data["Iterations"][1]
        iteration["IterationDate"] = "20260331"

        model = CampaignConfigValidation(**data)

        assert model.current_iteration
