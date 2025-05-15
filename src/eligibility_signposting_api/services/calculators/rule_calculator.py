from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from hamcrest.core.string_description import StringDescription

from eligibility_signposting_api.model import eligibility, rules
from eligibility_signposting_api.services.rules.operators import OperatorRegistry

Row = Collection[Mapping[str, Any]]


@dataclass
class RuleCalculator:
    person_data: Row
    rule: rules.IterationRule

    def evaluate_exclusion(self) -> tuple[eligibility.Status, eligibility.Reason]:
        """Evaluate if a particular rule excludes this person. Return the result, and the reason for the result."""
        attribute_value = self.get_attribute_value()
        status, reason = self.evaluate_rule(attribute_value)
        reason = eligibility.Reason(
            rule_name=eligibility.RuleName(self.rule.name),
            rule_type=eligibility.RuleType(self.rule.type),
            rule_result=eligibility.RuleResult(
                f"Rule {self.rule.name!r} ({self.rule.description!r}) "
                f"{'' if status.is_exclusion else 'not '}excluding - "
                f"{self.rule.attribute_name!r} {self.rule.comparator!r} {reason}"
            ),
        )
        return status, reason

    def get_attribute_value(self) -> str | None:
        """Pull out the correct attribute for a rule from the person's data."""
        match self.rule.attribute_level:
            case rules.RuleAttributeLevel.PERSON:
                person: Mapping[str, str | None] | None = next(
                    (r for r in self.person_data if r.get("ATTRIBUTE_TYPE", "") == "PERSON"), None
                )
                attribute_value = person.get(self.rule.attribute_name) if person else None
            case _:  # pragma: no cover
                msg = f"{self.rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    def evaluate_rule(self, attribute_value: str | None) -> tuple[eligibility.Status, str]:
        """Evaluate a rule against a person data attribute. Return the result, and the reason for the result."""
        matcher_class = OperatorRegistry.get(self.rule.operator)
        matcher = matcher_class(rule_value=self.rule.comparator)

        reason = StringDescription()
        if matcher.matches(attribute_value):
            matcher.describe_match(attribute_value, reason)
            status = {
                rules.RuleType.filter: eligibility.Status.not_eligible,
                rules.RuleType.suppression: eligibility.Status.not_actionable,
            }[self.rule.type]
            return status, str(reason)
        matcher.describe_mismatch(attribute_value, reason)
        return eligibility.Status.actionable, str(reason)
