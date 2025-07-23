from itertools import groupby
from operator import attrgetter
from typing import Iterable, Collection, Mapping, Any

from eligibility_signposting_api.model.eligibility_status import CohortGroupResult, Status
from eligibility_signposting_api.model.rules import IterationRule, IterationCohort
from eligibility_signposting_api.services.rules.rules_evaluator import RulesEvaluatorInterface

Row = Collection[Mapping[str, Any]]

class SuitabilityRulesEvaluator(RulesEvaluatorInterface):
    def __init__(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        suppression_rules: Iterable[IterationRule],
        person_data: Row
    ):
        self.cohort = cohort
        self.cohort_results = cohort_results
        self.suppression_rules = suppression_rules
        self.person_data = person_data

    def evaluate_suppression_rules(
        self
    ) -> None:
        is_actionable: bool = True
        priority_getter = attrgetter("priority")
        suppression_reasons = []

        sorted_rules_by_priority = sorted(self.get_exclusion_rules(self.cohort, self.suppression_rules), key=priority_getter)

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_exclusion_reasons, rule_stop = self.evaluate_rules_priority_group(rule_group, self.person_data)
            if status.is_exclusion:
                is_actionable = False
                suppression_reasons.extend(group_exclusion_reasons)
                if rule_stop:
                    break

        if self.cohort.cohort_label is not None:
            key = self.cohort.cohort_label
            if is_actionable:
                self.cohort_results[key] = CohortGroupResult(
                    self.cohort.cohort_group, Status.actionable, [], self.cohort.positive_description, suppression_reasons
                )
            else:
                self.cohort_results[key] = CohortGroupResult(
                    self.cohort.cohort_group,
                    Status.not_actionable,
                    suppression_reasons,
                    self.cohort.positive_description,
                    suppression_reasons,
                )
