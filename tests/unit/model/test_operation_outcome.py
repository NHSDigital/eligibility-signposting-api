"""
Unit tests for FHIR OperationOutcome models.

Tests the custom pydantic OperationOutcome and OperationOutcomeIssue models
that provide FHIR-compliant error responses without the heavyweight fhir-resources package.
"""

import json
from datetime import UTC, datetime

import pytest
from hamcrest import assert_that, equal_to, has_entries, has_entry, has_key, is_not, none
from pydantic import ValidationError

from eligibility_signposting_api.model.operation_outcome import OperationOutcome, OperationOutcomeIssue
from tests.fixtures.matchers.operation_outcome import is_operation_outcome, is_operation_outcome_issue


class TestOperationOutcomeIssue:
    """Tests for the OperationOutcomeIssue pydantic model."""

    def test_create_issue_with_all_fields(self):
        """Test creating an issue with all required and optional fields."""
        # Given
        coding_details = {
            "coding": [
                {
                    "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                    "code": "ACCESS_DENIED",
                    "display": "Access has been denied to process this request.",
                }
            ]
        }

        # When
        issue = OperationOutcomeIssue(
            severity="error",
            code="forbidden",
            details=coding_details,
            diagnostics="Access denied",
            location=["parameters/nhs-number"],
        )

        # Then
        assert_that(
            issue,
            is_operation_outcome_issue()
            .with_severity("error")
            .and_code("forbidden")
            .and_diagnostics("Access denied")
            .and_details(coding_details)
            .and_location(["parameters/nhs-number"]),
        )

    def test_create_issue_without_location(self):
        """Test creating an issue without the optional location field."""
        # Given, When
        issue = OperationOutcomeIssue(
            severity="warning",
            code="processing",
            details={"coding": []},
            diagnostics="Some warning",
        )

        # Then
        assert_that(issue, is_operation_outcome_issue().with_location(none()))

    def test_model_dump_includes_all_fields_when_location_present(self):
        """Test that model_dump() includes all fields when location is provided."""
        # Given
        issue = OperationOutcomeIssue(
            severity="error",
            code="value",
            details={"coding": []},
            diagnostics="Invalid value",
            location=["parameters/condition"],
        )

        # When
        result = issue.model_dump()

        # Then
        assert_that(
            result,
            has_entries(
                severity="error",
                code="value",
                diagnostics="Invalid value",
                details={"coding": []},
                location=["parameters/condition"],
            ),
        )

    def test_model_dump_excludes_none_excludes_none_location(self):
        """Test that model_dump(exclude_none=True) excludes location field when it's None."""
        # Given
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")

        # When
        result = issue.model_dump(exclude_none=True)

        # Then
        assert_that(result, is_not(has_key("location")))
        assert_that(result, has_key("severity"))
        assert_that(result, has_key("code"))
        assert_that(result, has_key("diagnostics"))
        assert_that(result, has_key("details"))

    def test_validation_error_on_missing_required_field(self):
        """Test that ValidationError is raised when required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            OperationOutcomeIssue(
                severity="error",
                code="processing",
                # Missing required 'diagnostics' and 'details'
            )

        assert "diagnostics" in str(exc_info.value) or "details" in str(exc_info.value)

    def test_validation_error_on_extra_field(self):
        """Test that extra fields are rejected due to extra='forbid'."""
        with pytest.raises(ValidationError) as exc_info:
            OperationOutcomeIssue(
                severity="error",
                code="processing",
                details={},
                diagnostics="Error",
                unexpected_field="value",
            )

        assert "unexpected_field" in str(exc_info.value)


class TestOperationOutcome:
    """Tests for the OperationOutcome pydantic model."""

    def test_create_operation_outcome_with_required_fields(self):
        """Test creating an OperationOutcome with only required fields."""
        # Given
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")

        # When
        outcome = OperationOutcome(issue=[issue])

        # Then
        assert_that(
            outcome,
            is_operation_outcome()
            .with_resourceType("OperationOutcome")
            .and_id(none())
            .and_meta(equal_to({}))
            .and_issue([issue]),
        )

    def test_create_operation_outcome_with_all_fields(self):
        """Test creating an OperationOutcome with all fields."""
        # Given
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")
        test_id = "test-id-123"
        test_meta = {"lastUpdated": datetime.now(UTC)}

        # When
        outcome = OperationOutcome(issue=[issue], id=test_id, meta=test_meta)

        # Then
        assert_that(
            outcome,
            is_operation_outcome().with_resourceType("OperationOutcome").and_id(test_id).and_meta(test_meta),
        )

    def test_resource_type_is_always_operation_outcome(self):
        """Test that resourceType is always 'OperationOutcome' and cannot be changed."""
        # Given
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")
        outcome = OperationOutcome(issue=[issue])

        # When, Then
        assert_that(outcome, is_operation_outcome().with_resourceType("OperationOutcome"))

        with pytest.raises(ValidationError):
            outcome.resourceType = "SomethingElse"

    def test_model_dump_with_all_fields(self):
        """Test that model_dump() produces correct structure with all fields."""
        # Given
        issue = OperationOutcomeIssue(
            severity="error",
            code="processing",
            details={"coding": []},
            diagnostics="Error message",
            location=["param"],
        )
        outcome = OperationOutcome(issue=[issue], id="abc-123", meta={"version": "1"})

        # When
        result = outcome.model_dump()

        # Then
        assert_that(
            result,
            has_entries(
                resourceType="OperationOutcome",
                id="abc-123",
                meta={"version": "1"},
            ),
        )
        assert_that(result["issue"][0], has_entry("severity", "error"))

    def test_model_dump_exclude_none_excludes_none_id(self):
        """Test that model_dump(exclude_none=True) excludes id field when it's None."""
        # Given
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")
        outcome = OperationOutcome(issue=[issue])

        # When
        result = outcome.model_dump(exclude_none=True)

        # Then
        assert_that(result, is_not(has_key("id")))
        assert_that(result, has_key("resourceType"))
        assert_that(result, has_key("issue"))

    def test_model_dump_mode_json_with_datetime(self):
        """Test that mode='json' serializes datetime objects to ISO strings."""
        # Given
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")
        test_datetime = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
        outcome = OperationOutcome(issue=[issue], meta={"lastUpdated": test_datetime})

        # When
        result = outcome.model_dump(mode="json")

        # Then
        assert_that(result, has_key("meta"))
        assert_that(result["meta"], has_entry("lastUpdated", "2024-01-15T10:30:45Z"))

    def test_model_dump_exclude_defaults_removes_empty_meta(self):
        """Test that model_dump with exclude_defaults removes default empty meta."""
        # Given
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")
        outcome = OperationOutcome(issue=[issue])

        # When
        result = outcome.model_dump(exclude_defaults=True)

        # Then
        assert_that(result, is_not(has_key("meta")))

    def test_multiple_issues(self):
        """Test OperationOutcome with multiple issues."""
        # Given
        issue1 = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error 1")
        issue2 = OperationOutcomeIssue(severity="warning", code="value", details={}, diagnostics="Warning 1")

        # When
        outcome = OperationOutcome(issue=[issue1, issue2])
        result = outcome.model_dump()

        # Then
        assert_that(result["issue"][0], has_entry("severity", "error"))
        assert_that(result["issue"][1], has_entry("severity", "warning"))

    def test_validation_error_on_empty_issue_list(self):
        """Test that ValidationError is raised when issue list is empty."""
        with pytest.raises(ValidationError) as exc_info:
            OperationOutcome(issue=[])

        assert "issue" in str(exc_info.value)

    def test_json_serialization_with_mode_json(self):
        """Test that the output can be serialized to JSON using mode='json'."""
        # Given
        issue = OperationOutcomeIssue(
            severity="error",
            code="forbidden",
            details={
                "coding": [
                    {
                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                        "code": "ACCESS_DENIED",
                        "display": "Access has been denied.",
                    }
                ]
            },
            diagnostics="Access denied",
            location=["parameters/nhs-number"],
        )
        outcome = OperationOutcome(issue=[issue], id="test-id", meta={"lastUpdated": datetime.now(UTC)})

        # When
        result = outcome.model_dump(mode="json", exclude_none=True)
        json_string = json.dumps(result)
        parsed = json.loads(json_string)

        # Then
        assert_that(parsed, has_entries(resourceType="OperationOutcome", id="test-id"))

    def test_fhir_compliant_structure(self):
        """Test that the output structure matches FHIR OperationOutcome specification."""
        # Given
        issue = OperationOutcomeIssue(
            severity="error",
            code="forbidden",
            details={
                "coding": [
                    {
                        "system": "https://fhir.nhs.uk/STU3/ValueSet/Spine-ErrorOrWarningCode-1",
                        "code": "ACCESS_DENIED",
                        "display": "Access has been denied to process this request.",
                    }
                ]
            },
            diagnostics="You are not authorised",
            location=["parameters/nhs-number"],
        )
        outcome = OperationOutcome(issue=[issue], id="123e4567-e89b-12d3-a456-426614174000")

        # When
        result = outcome.model_dump()

        # Then
        assert_that(
            result,
            has_entries(
                resourceType="OperationOutcome",
                id="123e4567-e89b-12d3-a456-426614174000",
            ),
        )
        assert_that(result, has_key("issue"))
        assert_that(
            result["issue"][0],
            has_entries(
                severity="error",
                code="forbidden",
                diagnostics="You are not authorised",
            ),
        )
        assert_that(result["issue"][0]["details"], has_key("coding"))

    def test_model_validation_with_pydantic(self):
        """Test that pydantic validation works correctly."""
        # Given, When
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")
        outcome = OperationOutcome(issue=[issue])

        # Then
        assert_that(
            outcome,
            is_operation_outcome().with_resourceType("OperationOutcome").and_issue([issue]),
        )

    def test_validation_error_on_extra_field(self):
        """Test that extra fields are rejected due to extra='forbid'."""
        issue = OperationOutcomeIssue(severity="error", code="processing", details={}, diagnostics="Error")

        with pytest.raises(ValidationError) as exc_info:
            OperationOutcome(issue=[issue], unexpected_field="value")

        assert "unexpected_field" in str(exc_info.value)
