from typing import Self

from pydantic import model_validator

from eligibility_signposting_api.model.campaign_config import IterationRule, RuleAttributeLevel, RuleAttributeName


class IterationRuleValidation(IterationRule):
    @model_validator(mode="after")
    def check_cohort_attribute_name(self) -> Self:
        if (
            self.attribute_level == RuleAttributeLevel.COHORT
            and self.attribute_name
            and self.attribute_name != RuleAttributeName("COHORT_LABEL")
        ):
            msg = ("When attribute_level is COHORT,"
                   " attribute_name must be COHORT_LABEL or None (default value is COHORT_LABEL).")
            raise ValueError(msg)
        return self
