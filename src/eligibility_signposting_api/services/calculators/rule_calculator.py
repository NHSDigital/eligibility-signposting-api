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
        status, reason, matcher_matched = self.evaluate_rule(attribute_value)
        reason = eligibility.Reason(
            rule_name=eligibility.RuleName(self.rule.name),
            rule_type=eligibility.RuleType(self.rule.type),
            rule_description=eligibility.RuleDescription(self.rule.description),
            matcher_matched=matcher_matched,
        )
        return status, reason

    def get_attribute_value(self) -> str | None:
        """Pull out the correct attribute for a rule from the person's data."""
        match self.rule.attribute_level:
            case rules.RuleAttributeLevel.PERSON:
                person: Mapping[str, str | None] | None = next(
                    (r for r in self.person_data if r.get("ATTRIBUTE_TYPE", "") == "PERSON"), None
                )
                attribute_value = person.get(str(self.rule.attribute_name)) if person else None
            case rules.RuleAttributeLevel.COHORT:
                cohorts: Mapping[str, str | None] | None = next(
                    (r for r in self.person_data if r.get("ATTRIBUTE_TYPE", "") == "COHORTS"), None
                )
                if cohorts:
                    attr_name = (
                        "COHORT_MAP"
                        if not self.rule.attribute_name or self.rule.attribute_name == "COHORT_LABEL"
                        else self.rule.attribute_name
                    )
                    cohort_map = self.get_value(cohorts, attr_name)
                    cohorts_dict = self.get_value(cohort_map, "cohorts")
                    m_dict = self.get_value(cohorts_dict, "M")
                    person_cohorts: set[str] = set(m_dict.keys())
                    attribute_value = ",".join(person_cohorts)
                else:
                    attribute_value = None

            case rules.RuleAttributeLevel.TARGET:
                target: Mapping[str, str | None] | None = next(
                    (r for r in self.person_data if r.get("ATTRIBUTE_TYPE", "") == self.rule.attribute_target), None
                )
                attribute_value = target.get(str(self.rule.attribute_name)) if target else None
            case _:  # pragma: no cover
                msg = f"{self.rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    @staticmethod
    def get_value(dictionary: Mapping[str, Any] | None, key: str) -> dict:
        v = dictionary.get(key, {}) if isinstance(dictionary, dict) else {}
        return v if isinstance(v, dict) else {}

    def evaluate_rule(self, attribute_value: str | None) -> tuple[eligibility.Status, str, bool]:
        """Evaluate a rule against a person data attribute. Return the result, and the reason for the result."""
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
            }[self.rule.type]
            return status, str(reason), matcher_matched
        matcher.describe_mismatch(attribute_value, reason)
        return eligibility.Status.actionable, str(reason), matcher_matched
