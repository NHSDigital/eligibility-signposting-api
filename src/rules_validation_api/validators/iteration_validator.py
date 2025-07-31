from pydantic import Field

from eligibility_signposting_api.model.campaign_config import Iteration
from rules_validation_api.validators.actions_mapper_validator import ActionsMapperValidator
from rules_validation_api.validators.iteration_rules_validator import IterationRuleValidation


class IterationValidation(Iteration):
    iteration_rules: list[IterationRuleValidation] = Field(..., alias="IterationRules")
    actions_mapper: ActionsMapperValidator = Field(..., alias="ActionsMapper")

