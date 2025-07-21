from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from eligibility_signposting_api.model import rules
from eligibility_signposting_api.model.types import Row


@dataclass
class PersonDataReader:
    person_data: Row

    @property
    def person_cohorts(self) -> set[str]:
        cohorts_row: Mapping[str, dict[str, dict[str, dict[str, Any]]]] = next(
            (row for row in self.person_data if row.get("ATTRIBUTE_TYPE") == "COHORTS"),
            {},
        )
        return set(cohorts_row.get("COHORT_MAP", {}).get("cohorts", {}).get("M", {}).keys())

    def get_attribute_value(self, rule: rules.IterationRule) -> str | None:
        """Pull out the correct attribute for a rule from the person's data."""
        match rule.attribute_level:
            case rules.RuleAttributeLevel.PERSON:
                person: Mapping[str, str | None] | None = next(
                    (r for r in self.person_data if r.get("ATTRIBUTE_TYPE", "") == "PERSON"), None
                )
                attribute_value = person.get(str(rule.attribute_name)) if person else None
            case rules.RuleAttributeLevel.COHORT:
                cohorts: Mapping[str, str | None] | None = next(
                    (r for r in self.person_data if r.get("ATTRIBUTE_TYPE", "") == "COHORTS"), None
                )
                if cohorts:
                    attr_name = (
                        "COHORT_MAP"
                        if not rule.attribute_name or rule.attribute_name == "COHORT_LABEL"
                        else rule.attribute_name
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
                    (r for r in self.person_data if r.get("ATTRIBUTE_TYPE", "") == rule.attribute_target), None
                )
                attribute_value = target.get(str(rule.attribute_name)) if target else None
            case _:  # pragma: no cover
                msg = f"{rule.attribute_level} not implemented"
                raise NotImplementedError(msg)
        return attribute_value

    @staticmethod
    def get_value(dictionary: Mapping[str, Any] | None, key: str) -> dict:
        v = dictionary.get(key, {}) if isinstance(dictionary, dict) else {}
        return v if isinstance(v, dict) else {}
