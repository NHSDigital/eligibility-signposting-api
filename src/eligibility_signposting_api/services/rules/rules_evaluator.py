from typing import Iterable, Iterator, Collection, Mapping, Any

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.eligibility_status import Status
from eligibility_signposting_api.model.rules import IterationCohort, IterationRule
from eligibility_signposting_api.services.calculators.rule_calculator import RuleCalculator

Row = Collection[Mapping[str, Any]]

class RulesEvaluatorInterface:
    @staticmethod
    def get_exclusion_rules(
        cohort: IterationCohort, filter_rules: Iterable[IterationRule]
    ) -> Iterator[IterationRule]:
        return (
            ir for ir in filter_rules
            if ir.cohort_label is None
            or cohort.cohort_label == ir.cohort_label
            or (isinstance(ir.cohort_label, (list, set, tuple)) and cohort.cohort_label in ir.cohort_label)
        )

    @staticmethod
    def evaluate_rules_priority_group(
        rules_group: Iterator[IterationRule], person_data: Row
    ) -> tuple[Status, list[eligibility_status.Reason], bool]:
        is_rule_stop = False
        exclusion_reasons = []
        best_status = Status.not_eligible

        for rule in rules_group:
            is_rule_stop = rule.rule_stop or is_rule_stop
            rule_calculator = RuleCalculator(person_data=person_data, rule=rule)
            status, reason = rule_calculator.evaluate_exclusion()
            if status.is_exclusion:
                best_status = Status.best(status, best_status)
                exclusion_reasons.append(reason)
            else:
                best_status = Status.actionable

        return best_status, exclusion_reasons, is_rule_stop
