from __future__ import annotations

from dataclasses import dataclass

from hamcrest.core.string_description import StringDescription

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.services.calculators.person_data_reader import PersonDataReader
from eligibility_signposting_api.services.rules.operators import OperatorRegistry


@dataclass
class RuleCalculator:
    person_data_reader: PersonDataReader
    rule: rules.IterationRule

    def evaluate_exclusion(self) -> tuple[eligibility.Status, eligibility.Reason]:
        """Evaluate if a particular rule excludes this person. Return the result, and the reason for the result."""

        attribute_value = self.person_data_reader.get_attribute_value(self.rule)
        status, reason, matcher_matched = self.evaluate_rule(attribute_value)
        reason = eligibility.Reason(
            rule_name=eligibility.RuleName(self.rule.name),
            rule_type=eligibility.RuleType(self.rule.type),
            rule_priority=eligibility.RulePriority(str(self.rule.priority)),
            rule_description=eligibility.RuleDescription(self.rule.description),
            matcher_matched=matcher_matched,
        )
        return status, reason

    def evaluate_rule(self, attribute_value: str | None) -> tuple[eligibility.Status, str, bool]:
        """Evaluate a rule against a person's data attribute. Return the result, and the reason for the result."""
        matcher_class = OperatorRegistry.get(self.rule.operator)
        matcher = matcher_class(rule_value=self.rule.comparator)

        matcher_matched = matcher.matches(attribute_value)
        reason = StringDescription()
        if matcher_matched:
            matcher.describe_match(attribute_value, reason)
            status = {
                rules.RuleType.filter: eligibility.Status.not_eligible,
                rules.RuleType.suppression: eligibility.Status.not_actionable,
                rules.RuleType.redirect: eligibility.Status.actionable,
                rules.RuleType.not_eligible_actions: eligibility.Status.not_eligible,
                rules.RuleType.not_actionable_actions: eligibility.Status.not_actionable,
            }[self.rule.type]
            return status, str(reason), matcher_matched
        matcher.describe_mismatch(attribute_value, reason)
        return eligibility.Status.actionable, str(reason), matcher_matched
