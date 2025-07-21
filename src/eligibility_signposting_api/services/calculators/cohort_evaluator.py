from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.model.eligibility import CohortGroupResult, Status
from eligibility_signposting_api.model.rules import Iteration, IterationCohort
from eligibility_signposting_api.services.calculators.person_data_reader import PersonDataReader
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator


@dataclass
class CohortEvaluator:
    person_data_reader: PersonDataReader

    def get_cohort_results(self, active_iteration: rules.Iteration) -> dict[str, CohortGroupResult]:
        cohort_results: dict[str, CohortGroupResult] = {}
        filter_rules, suppression_rules = self.get_rules_by_type(active_iteration)
        for cohort in sorted(active_iteration.iteration_cohorts, key=attrgetter("priority")):
            # Base Eligibility - check
            if cohort.cohort_label in self.person_data_reader.person_cohorts or cohort.is_magic_cohort:
                # Eligibility - check
                if self.is_eligible_by_filter_rules(cohort, cohort_results, filter_rules):
                    # Actionability - evaluation
                    self.evaluate_suppression_rules(cohort, cohort_results, suppression_rules)

            # Not base eligible
            elif cohort.cohort_label is not None:
                cohort_results[cohort.cohort_label] = CohortGroupResult(
                    cohort.cohort_group,
                    Status.not_eligible,
                    [],
                    cohort.negative_description,
                    [],
                )
        return cohort_results

    @staticmethod
    def get_the_best_cohort_memberships(
        cohort_results: dict[str, CohortGroupResult],
    ) -> tuple[Status, list[CohortGroupResult]]:
        if not cohort_results:
            return eligibility.Status.not_eligible, []

        best_status = eligibility.Status.best(*[result.status for result in cohort_results.values()])
        best_cohorts = [result for result in cohort_results.values() if result.status == best_status]

        best_cohorts = [
            CohortGroupResult(
                cohort_code=cc.cohort_code,
                status=cc.status,
                reasons=cc.reasons,
                description=(cc.description or "").strip() if cc.description else "",
                audit_rules=cc.audit_rules,
            )
            for cc in best_cohorts
        ]

        return best_status, best_cohorts

    @staticmethod
    def get_exclusion_rules(
        cohort: IterationCohort, filter_rules: Iterable[rules.IterationRule]
    ) -> Iterator[rules.IterationRule]:
        return (
            ir
            for ir in filter_rules
            if ir.cohort_label is None
            or cohort.cohort_label == ir.cohort_label
            or (isinstance(ir.cohort_label, (list, set, tuple)) and cohort.cohort_label in ir.cohort_label)
        )

    @staticmethod
    def get_rules_by_type(
        active_iteration: Iteration,
    ) -> tuple[tuple[rules.IterationRule, ...], tuple[rules.IterationRule, ...]]:
        filter_rules, suppression_rules = (
            tuple(rule for rule in active_iteration.iteration_rules if attrgetter("type")(rule) == rule_type)
            for rule_type in (rules.RuleType.filter, rules.RuleType.suppression)
        )
        return filter_rules, suppression_rules

    def is_eligible_by_filter_rules(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        filter_rules: Iterable[rules.IterationRule],
    ) -> bool:
        is_eligible = True
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, filter_rules), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_exclusion_reasons, _ = self.evaluate_rules_priority_group(rule_group)
            if status.is_exclusion:
                if cohort.cohort_label is not None:
                    cohort_results[cohort.cohort_label] = CohortGroupResult(
                        (cohort.cohort_group),
                        Status.not_eligible,
                        [],
                        cohort.negative_description,
                        group_exclusion_reasons,
                    )
                is_eligible = False
                break
        return is_eligible

    def evaluate_suppression_rules(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        suppression_rules: Iterable[rules.IterationRule],
    ) -> None:
        is_actionable: bool = True
        priority_getter = attrgetter("priority")
        suppression_reasons = []

        sorted_rules_by_priority = sorted(self.get_exclusion_rules(cohort, suppression_rules), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_exclusion_reasons, rule_stop = self.evaluate_rules_priority_group(rule_group)
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
        self, rules_group: Iterator[rules.IterationRule]
    ) -> tuple[eligibility.Status, list[eligibility.Reason], bool]:
        is_rule_stop = False
        exclusion_reasons = []
        best_status = eligibility.Status.not_eligible

        for rule in rules_group:
            is_rule_stop = rule.rule_stop or is_rule_stop
            rule_calculator = RuleCalculator(person_data_reader=self.person_data_reader, rule=rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status = eligibility.Status.best(status, best_status)
                exclusion_reasons.append(reason)
            else:
                best_status = eligibility.Status.actionable

        return best_status, exclusion_reasons, is_rule_stop
