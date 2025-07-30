from pydantic import Field, field_validator

from eligibility_signposting_api.model.campaign_config import Iteration
from rules_validation_api.validators.iteration_rules_validator import IterationRuleValidation


class IterationValidation(Iteration):
    iteration_rules: list[IterationRuleValidation] = Field(..., alias="IterationRules")
