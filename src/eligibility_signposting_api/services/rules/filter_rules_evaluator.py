from itertools import groupby
from operator import attrgetter
from typing import Iterable, Collection, Mapping, Any

from eligibility_signposting_api.model.eligibility_status import CohortGroupResult, Status
from eligibility_signposting_api.model.rules import IterationRule, IterationCohort
from eligibility_signposting_api.services.rules.rules_evaluator import RulesEvaluatorInterface

Row = Collection[Mapping[str, Any]]

class FilterRulesEvaluator(RulesEvaluatorInterface):
    def __init__(
        self,
        cohort: IterationCohort,
        cohort_results: dict[str, CohortGroupResult],
        filter_rules: Iterable[IterationRule],
        person_data: Row
    ):
        self.cohort = cohort
        self.cohort_results = cohort_results
        self.filter_rules = filter_rules
        self.person_data = person_data

    def is_eligible(self) -> bool:
        is_eligible = True
        priority_getter = attrgetter("priority")
        sorted_rules_by_priority = sorted(
            self.get_exclusion_rules(self.cohort, self.filter_rules),
            key=priority_getter
        )

        for _, rule_group in groupby(sorted_rules_by_priority, key=priority_getter):
            status, group_exclusion_reasons, _ = self.evaluate_rules_priority_group(rule_group, self.person_data)
            if status.is_exclusion:
                if self.cohort.cohort_label is not None:
                    self.cohort_results[self.cohort.cohort_label] = CohortGroupResult(
                        self.cohort.cohort_group,
                        Status.not_eligible,
                        [],
                        self.cohort.negative_description,
                        group_exclusion_reasons,
                    )
                is_eligible = False
                break
        return is_eligible
