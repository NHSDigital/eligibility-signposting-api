from typing import Self

from pydantic import model_validator

from eligibility_signposting_api.model.campaign_config import (
    IterationRule,
    RuleAttributeLevel,
    RuleAttributeName,
    RuleType,
)


class IterationRuleValidation(IterationRule):
    @model_validator(mode="after")
    def check_cohort_attribute_name(self) -> Self:
        if (
            self.attribute_level == RuleAttributeLevel.COHORT
            and self.attribute_name
            and self.attribute_name != RuleAttributeName("COHORT_LABEL")
        ):
            msg = "When attribute_level is COHORT, attribute_name must be COHORT_LABEL or None (default:COHORT_LABEL)"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def check_cohort_label_for_non_f_and_s_types(self) -> Self:
        allowed_types = {RuleType("F"), RuleType("S")}
        if self.cohort_label is not None and self.type not in allowed_types:
            msg = (
                f"CohortLabel is only allowed for rule types F and S. "
                f"Found type: {self.type} with cohort_label: {self.cohort_label}"
            )
            raise ValueError(msg)
        return self
