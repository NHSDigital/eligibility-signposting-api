from __future__ import annotations

from dataclasses import dataclass, field
from itertools import groupby
from operator import attrgetter
from typing import TYPE_CHECKING

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import Iteration, IterationCohort, IterationRule, RuleType
from eligibility_signposting_api.model.eligibility_status import CohortGroupResult, Status
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator
from eligibility_signposting_api.services.processors.person_data_reader import PersonDataReader

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from eligibility_signposting_api.model.person import Person


@dataclass
class RuleProcessor:
    """Handles the processing and evaluation of different rules (filter, suppression) against person data."""

    person_data_reader: PersonDataReader = field(default_factory=PersonDataReader)

    def is_eligible(
        self,
        person: Person,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        filter_rules: Iterable[IterationRule],
    ) -> bool:
        is_eligible = True
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, filter_rules), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_exclusion_reasons, _ = self.evaluate_rules_priority_group(person, rule_group)
            if status.is_exclusion:
                if cohort.cohort_label is not None:
                    cohort_results[cohort.cohort_label] = CohortGroupResult(
                        cohort.cohort_group,
                        Status.not_eligible,
                        [],
                        cohort.negative_description,
                        group_exclusion_reasons,
                    )
                is_eligible = False
                break
        return is_eligible

    def is_actionable(
        self,
        person: Person,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        suppression_rules: Iterable[IterationRule],
    ) -> None:
        is_actionable: bool = True
        priority_getter = attrgetter("priority")
        suppression_reasons = []

        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, suppression_rules), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_exclusion_reasons, rule_stop = self.evaluate_rules_priority_group(person, rule_group)
            if status.is_exclusion:
                is_actionable = False
                suppression_reasons.extend(group_exclusion_reasons)
                if rule_stop:
                    break

        if cohort.cohort_label is not None:
            key = cohort.cohort_label
            if is_actionable:
                cohort_results[key] = CohortGroupResult(
                    cohort.cohort_group, Status.actionable, [], cohort.positive_description, suppression_reasons
                )
            else:
                cohort_results[key] = CohortGroupResult(
                    cohort.cohort_group,
                    Status.not_actionable,
                    suppression_reasons,
                    cohort.positive_description,
                    suppression_reasons,
                )

    def evaluate_rules_priority_group(
        self, person: Person, rules_group: Iterator[IterationRule]
    ) -> tuple[eligibility_status.Status, list[eligibility_status.Reason], bool]:
        is_rule_stop = False
        exclusion_reasons = []
        best_status = eligibility_status.Status.not_eligible

        for rule in rules_group:
            is_rule_stop = rule.rule_stop or is_rule_stop
            rule_calculator = RuleCalculator(person=person, rule=rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status = eligibility_status.Status.best(status, best_status)
                exclusion_reasons.append(reason)
            else:
                best_status = eligibility_status.Status.actionable

        return best_status, exclusion_reasons, is_rule_stop

    @staticmethod
    def get_exclusion_rules(cohort: IterationCohort, rules: Iterable[IterationRule]) -> Iterator[IterationRule]:
        return (
            ir
            for ir in rules
            if ir.cohort_label is None
            or cohort.cohort_label == ir.cohort_label
            or (isinstance(ir.cohort_label, (list, set, tuple)) and cohort.cohort_label in ir.cohort_label)
        )

    # TODO: add unit tests
    def get_cohort_group_results(self, person: Person, active_iteration: Iteration) -> dict[str, CohortGroupResult]:
        cohort_results: dict[str, CohortGroupResult] = {}
        filter_rules, suppression_rules = self.get_rules_by_type(active_iteration)

        for cohort in sorted(active_iteration.iteration_cohorts, key=attrgetter("priority")):
            if self.is_base_eligible(person, cohort):
                if self.is_eligible(person, cohort, cohort_results, filter_rules):
                    self.is_actionable(person, cohort, cohort_results, suppression_rules)
            else:
                cohort_results = self.get_not_base_eligible_results(cohort, cohort_results)

        return cohort_results

    def get_not_base_eligible_results(
        self, cohort: IterationCohort, cohort_results: dict[str, CohortGroupResult]
    ) -> dict[str, CohortGroupResult]:
        cohort_results[cohort.cohort_label] = CohortGroupResult(
            cohort.cohort_group,
            Status.not_eligible,
            [],
            cohort.negative_description,
            [],
        )
        return cohort_results

    def is_base_eligible(self, person: Person, cohort: IterationCohort) -> bool:
        person_cohorts = self.person_data_reader.get_person_cohorts(person)
        return cohort.cohort_label in person_cohorts or cohort.is_magic_cohort

    @staticmethod
    def get_rules_by_type(active_iteration: Iteration) -> tuple[tuple[IterationRule, ...], tuple[IterationRule, ...]]:
        filter_rules, suppression_rules = (
            tuple(rule for rule in active_iteration.iteration_rules if attrgetter("type")(rule) == rule_type)
            for rule_type in (RuleType.filter, RuleType.suppression)
        )
        return filter_rules, suppression_rules
