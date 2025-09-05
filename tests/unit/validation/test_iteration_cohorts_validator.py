import pytest
from pydantic import ValidationError

from eligibility_signposting_api.model.campaign_config import Virtual
from rules_validation_api.validators.iteration_cohort_validator import IterationCohortValidation


class TestMandatoryFieldsSchemaValidations:
    def test_missing_cohort_label_raises_error(self):
        data = {"CohortGroup": "rsv_age_rolling"}
        with pytest.raises(ValidationError) as exc_info:
            IterationCohortValidation(**data)
        assert "CohortLabel" in str(exc_info.value)

    def test_missing_cohort_group_raises_error(self):
        data = {"CohortLabel": "rsv_75_rolling"}
        with pytest.raises(ValidationError) as exc_info:
            IterationCohortValidation(**data)
        assert "CohortGroup" in str(exc_info.value)

    def test_valid_with_only_mandatory_fields(self):
        data = {"CohortLabel": "rsv_75_rolling", "CohortGroup": "rsv_age_rolling"}
        cohort = IterationCohortValidation(**data)
        assert cohort.cohort_label == "rsv_75_rolling"
        assert cohort.cohort_group == "rsv_age_rolling"


class TestOptionalFieldsSchemaValidations:
    def test_positive_description_can_be_none(self):
        data = {"CohortLabel": "rsv_75_rolling", "CohortGroup": "rsv_age_rolling", "PositiveDescription": None}
        cohort = IterationCohortValidation(**data)
        assert cohort.positive_description is None

    def test_negative_description_can_be_none(self):
        data = {"CohortLabel": "rsv_75_rolling", "CohortGroup": "rsv_age_rolling", "NegativeDescription": None}
        cohort = IterationCohortValidation(**data)
        assert cohort.negative_description is None

    def test_priority_can_be_none(self):
        data = {"CohortLabel": "rsv_75_rolling", "CohortGroup": "rsv_age_rolling", "Priority": None}
        cohort = IterationCohortValidation(**data)
        assert cohort.priority is None

    def test_positive_description_accepts_valid_value(self):
        data = {
            "CohortLabel": "rsv_75_rolling",
            "CohortGroup": "rsv_age_rolling",
            "PositiveDescription": "Eligible for benefits",
        }
        cohort = IterationCohortValidation(**data)
        assert cohort.positive_description == "Eligible for benefits"

    def test_negative_description_accepts_valid_value(self):
        data = {
            "CohortLabel": "rsv_75_rolling",
            "CohortGroup": "rsv_age_rolling",
            "NegativeDescription": "Not eligible",
        }
        cohort = IterationCohortValidation(**data)
        assert cohort.negative_description == "Not eligible"

    def test_priority_accepts_valid_value(self):
        cohort_priority = 10
        data = {"CohortLabel": "rsv_75_rolling", "CohortGroup": "rsv_age_rolling", "Priority": cohort_priority}
        cohort = IterationCohortValidation(**data)
        assert cohort.priority == cohort_priority

    def test_virtual_valid_value(self):  # TODO Done : parse iteration_cohort and check  if the virtual value is N by default
        cohort_priority = 10
        data = {"CohortLabel": "rsv_75_rolling", "CohortGroup": "rsv_age_rolling", "Priority": cohort_priority}
        cohort = IterationCohortValidation(**data)
        assert cohort.virtual == Virtual.NO

    @pytest.mark.parametrize(
        ("virtual_str", "expected"),
        [
            ("Y", Virtual.YES),
            ("y", Virtual.YES),
            ("N", Virtual.NO),
            ("n", Virtual.NO),
            (None, Virtual.NO),
        ],
    )
    def test_virtual_valid_value_when_provided(self, virtual_str: str, expected: Virtual):  # TODO : Done - recheck
        cohort_priority = 10
        data = {
            "CohortLabel": "rsv_75_rolling",
            "CohortGroup": "rsv_age_rolling",
            "Priority": cohort_priority,
            "Virtual": virtual_str,
        }
        cohort = IterationCohortValidation(**data)
        assert cohort.virtual == expected

    @pytest.mark.parametrize("invalid_value", ["", "yes", "no", "1", "0", "true", "X", "Z"])
    def test_virtual_invalid_values_raise_error(self, invalid_value):  # TODO : Done - recheck
        data = {
            "CohortLabel": "rsv_75_rolling",
            "CohortGroup": "rsv_age_rolling",
            "Priority": 10,
            "Virtual": invalid_value,
        }
        with pytest.raises(ValidationError):
            IterationCohortValidation(**data)
