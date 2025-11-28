import typing

from pydantic import model_validator

from eligibility_signposting_api.model.campaign_config import (
    IterationRule,
    RuleAttributeLevel,
    RuleAttributeName,
    RuleType,
)
from rules_validation_api.decorators.tracker import track_validators


@track_validators
class IterationRuleValidation(IterationRule):
    @model_validator(mode="after")
    def check_cohort_attribute_name(self) -> typing.Self:
        if (
            self.attribute_level == RuleAttributeLevel.COHORT
            and self.attribute_name
            and self.attribute_name != RuleAttributeName("COHORT_LABEL")
        ):
            msg = "When attribute_level is COHORT, attribute_name must be COHORT_LABEL or None (default:COHORT_LABEL)"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def check_cohort_label_for_non_f_and_s_types(self) -> typing.Self:
        allowed_types = {RuleType("F"), RuleType("S")}
        if self.cohort_label is not None and self.type not in allowed_types:
            msg = (
                "CohortLabel is only allowed for rule types F and S. "
                f"Found type: {self.type} with cohort_label: {self.cohort_label}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_attribute_name_is_optional_only_for_cohort_attribute_level(self) -> typing.Self:
        if self.attribute_name:
            return self
        if self.attribute_level == RuleAttributeLevel.COHORT:
            return self
        msg = f"AttributeName must be set where AttributeLevel is {self.attribute_level}."
        raise ValueError(msg)

    @model_validator(mode="after")
    def validate_attribute_target_is_mandatory_for_target_attribute_level(self) -> typing.Self:
        if self.attribute_target:
            return self
        if self.attribute_level != RuleAttributeLevel.TARGET:
            return self
        msg = f"AttributeTarget is mandatory where AttributeLevel is {self.attribute_level}."
        raise ValueError(msg)
