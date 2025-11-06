from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from hamcrest.core.string_description import StringDescription

from eligibility_signposting_api.model import eligibility_status
from eligibility_signposting_api.model.campaign_config import IterationRule, RuleAttributeLevel, RuleType
from eligibility_signposting_api.services.operators.operators import OperatorRegistry
from eligibility_signposting_api.services.processors.person_data_reader import PersonDataReader

if TYPE_CHECKING:
    from collections.abc import Mapping

    from eligibility_signposting_api.model.person import Person


@dataclass
class RuleCalculator:
    person: Person
    rule: IterationRule

    person_data_reader: PersonDataReader = field(default_factory=PersonDataReader)

    def evaluate_exclusion(self) -> tuple[eligibility_status.Status, eligibility_status.Reason]:
        """Evaluate if a particular rule excludes this person. Return the result, and the reason for the result."""
        attribute_value = self.get_attribute_value()
        status, reason, matcher_matched = self.evaluate_rule(attribute_value)
        rule_code = eligibility_status.RuleCode(self.rule.rule_code)
        reason = eligibility_status.Reason(
            rule_name=eligibility_status.RuleName(self.rule.name),
            rule_code=rule_code,
            rule_type=eligibility_status.RuleType(self.rule.type),
            rule_priority=eligibility_status.RulePriority(str(self.rule.priority)),
            rule_text=eligibility_status.RuleText(self.rule.rule_text),
            matcher_matched=matcher_matched,
        )
        return status, reason

    def get_attribute_value(self) -> str | None:
        """Pull out the correct attribute for a rule from the person's data."""
        match self.rule.attribute_level:
            case RuleAttributeLevel.PERSON:
                person: Mapping[str, str | None] | None = next(
                    (r for r in self.person.data if r.get("ATTRIBUTE_TYPE", "") == "PERSON"), None
                )
                attribute_value = person.get(str(self.rule.attribute_name)) if person else None
            case RuleAttributeLevel.COHORT:
                cohorts: Mapping[str, str | None] | None = next(
                    (r for r in self.person.data if r.get("ATTRIBUTE_TYPE", "") == "COHORTS"), None
                )
                if cohorts:
                    person_cohorts = self.person_data_reader.get_person_cohorts(self.person)
                    attribute_value = ",".join(person_cohorts)
                else:
                    attribute_value = None

            case RuleAttributeLevel.TARGET:
                target: Mapping[str, str | None] | None = next(
                    (r for r in self.person.data if r.get("ATTRIBUTE_TYPE", "") == self.rule.attribute_target), None
                )
                attribute_value = target.get(str(self.rule.attribute_name)) if target else None
            case _:  # pragma: no cover
                msg = f"{self.rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    def evaluate_rule(self, attribute_value: str | None) -> tuple[eligibility_status.Status, str, bool]:
        """Evaluate a rule against a person data attribute. Return the result, and the reason for the result."""
        matcher_class = OperatorRegistry.get(self.rule.operator)
        matcher = matcher_class(rule_value=self.rule.comparator)

        matcher_matched = matcher.matches(attribute_value)
        reason = StringDescription()
        if matcher_matched:
            matcher.describe_match(attribute_value, reason)
            status = {
                RuleType.filter: eligibility_status.Status.not_eligible,
                RuleType.suppression: eligibility_status.Status.not_actionable,
                RuleType.redirect: eligibility_status.Status.actionable,
                RuleType.not_eligible_actions: eligibility_status.Status.not_eligible,
                RuleType.not_actionable_actions: eligibility_status.Status.not_actionable,
            }[self.rule.type]
            return status, str(reason), matcher_matched
        matcher.describe_mismatch(attribute_value, reason)
        return eligibility_status.Status.actionable, str(reason), matcher_matched
