from pydantic import Field, ValidationError, model_validator
from pydantic_core import InitErrorDetails

from eligibility_signposting_api.model.campaign_config import Iteration
from rules_validation_api.validators.actions_mapper_validator import ActionsMapperValidator
from rules_validation_api.validators.iteration_rules_validator import IterationRuleValidation


class IterationValidation(Iteration):
    iteration_rules: list[IterationRuleValidation] = Field(..., alias="IterationRules")
    actions_mapper: ActionsMapperValidator = Field(..., alias="ActionsMapper")

    @model_validator(mode="after")
    def validate_default_comms_routing_in_actions_mapper(self):
        default_routing = self.default_comms_routing
        actions_mapper = self.actions_mapper.root.keys()

        if default_routing:
            if not actions_mapper or default_routing not in actions_mapper:
                error = InitErrorDetails(
                    type='value_error',
                    loc=('actions_mapper',),
                    input=actions_mapper,
                    ctx={'error': f"Missing entry for DefaultCommsRouting '{default_routing}' in ActionsMapper"}
                )
                raise ValidationError.from_exception_data(
                    title='IterationValidation',
                    line_errors=[error]
                )

        return self
