"""
FHIR OperationOutcome models for API error responses.

Lightweight pydantic models for FHIR-compliant error responses without
requiring the heavyweight fhir-resources package.

See: https://www.hl7.org/fhir/operationoutcome.html
"""

from typing import Any

from pydantic import BaseModel, Field


class OperationOutcomeIssue(BaseModel):
    """
    FHIR OperationOutcome.Issue component.

    Represents a single issue associated with an action.
    """

    severity: str = Field(
        ...,
        description="fatal | error | warning | information",
    )
    code: str = Field(
        ...,
        description="FHIR issue type code",
    )
    details: dict[str, Any] = Field(
        ...,
        description="Additional details about the error (CodeableConcept)",
    )
    diagnostics: str = Field(
        ...,
        description="Additional diagnostic information about the issue",
    )
    location: list[str] | None = Field(
        default=None,
        description="FHIRPath of element(s) related to issue",
    )

    model_config = {"extra": "forbid"}


class OperationOutcome(BaseModel):
    """
    FHIR OperationOutcome resource.

    A collection of error, warning, or information messages that result
    from a system action.
    """

    resourceType: str = Field(  # noqa: N815
        default="OperationOutcome",
        frozen=True,
        description="FHIR resource type",
    )
    id: str | None = Field(
        default=None,
        description="Logical id of this artifact",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the resource",
    )
    issue: list[OperationOutcomeIssue] = Field(
        ...,
        min_length=1,
        description="A single issue associated with the action",
    )

    model_config = {"extra": "forbid"}
