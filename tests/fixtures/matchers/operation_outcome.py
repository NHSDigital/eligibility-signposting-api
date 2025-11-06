"""Hamcrest matchers for FHIR OperationOutcome models."""

from hamcrest.core.matcher import Matcher

from eligibility_signposting_api.model.operation_outcome import OperationOutcome, OperationOutcomeIssue

from .meta import BaseAutoMatcher


class OperationOutcomeIssueMatcher(BaseAutoMatcher[OperationOutcomeIssue]): ...


class OperationOutcomeMatcher(BaseAutoMatcher[OperationOutcome]): ...


def is_operation_outcome_issue() -> Matcher[OperationOutcomeIssue]:
    """Create a matcher for OperationOutcomeIssue."""
    return OperationOutcomeIssueMatcher()


def is_operation_outcome() -> Matcher[OperationOutcome]:
    """Create a matcher for OperationOutcome."""
    return OperationOutcomeMatcher()
