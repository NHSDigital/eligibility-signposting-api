from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from eligibility_signposting_api.model.eligibility_status import CohortGroupResult, Status

if TYPE_CHECKING:
    from collections.abc import Iterable

    from eligibility_signposting_api.model.campaign_config import IterationCohort, IterationRule
    from eligibility_signposting_api.model.person import Person
    from eligibility_signposting_api.services.processors.rule_processor import RuleProcessor


class CohortEligibilityHandler(ABC):
    """Abstract base class for eligibility/actionability handlers."""

    def __init__(self, next_handler: CohortEligibilityHandler | None = None) -> None:
        self.next_handler = next_handler

    @abstractmethod
    def handle(
        self,
        person: Person,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        rules_processor: RuleProcessor,
    ) -> None:
        """Handles a part of the eligibility/actionability check or passes to the next handler."""

    def next(self, next_handler: CohortEligibilityHandler) -> CohortEligibilityHandler:
        """Sets the next handler in the chain and returns this handler for chaining."""
        self.next_handler = next_handler
        return next_handler

    def pass_to_next(
        self,
        person: Person,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        rules_processor: RuleProcessor,
    ) -> None:
        """Passes the request to the next handler in the chain if one exists."""
        if self.next_handler:
            self.next_handler.handle(person, cohort, cohort_results, rules_processor)


class BaseEligibilityHandler(CohortEligibilityHandler):
    """Handles the base eligibility check (person in cohort or magic cohort)."""

    def handle(
        self,
        person: Person,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        rules_processor: RuleProcessor,
    ) -> None:
        if not rules_processor.is_base_eligible(person, cohort):
            cohort_results[cohort.cohort_label] = CohortGroupResult(
                cohort.cohort_group,
                Status.not_eligible,
                [],
                cohort.negative_description,
                [],
            )
            return

        self.pass_to_next(person, cohort, cohort_results, rules_processor)


class FilterRuleHandler(CohortEligibilityHandler):
    """Handles the eligibility check based on filter rules."""

    def __init__(
        self, filter_rules: Iterable[IterationRule], next_handler: CohortEligibilityHandler | None = None
    ) -> None:
        super().__init__(next_handler)
        self.filter_rules = filter_rules

    def handle(
        self,
        person: Person,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        rules_processor: RuleProcessor,
    ) -> None:
        if not rules_processor.is_eligible(person, cohort, cohort_results, self.filter_rules):
            return

        self.pass_to_next(person, cohort, cohort_results, rules_processor)


class SuppressionRuleHandler(CohortEligibilityHandler):
    """Handles the actionability check based on suppression rules."""

    def __init__(
        self, suppression_rules: Iterable[IterationRule], next_handler: CohortEligibilityHandler | None = None
    ) -> None:
        super().__init__(next_handler)
        self.suppression_rules = suppression_rules

    def handle(
        self,
        person: Person,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        rules_processor: RuleProcessor,
    ) -> None:
        rules_processor.is_actionable(person, cohort, cohort_results, self.suppression_rules)
