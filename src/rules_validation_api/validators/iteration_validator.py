import typing

from pydantic import ValidationError, field_validator, model_validator
from pydantic_core import InitErrorDetails

from eligibility_signposting_api.model.campaign_config import ActionsMapper, Iteration, IterationRule
from rules_validation_api.validators.actions_mapper_validator import ActionsMapperValidator
from rules_validation_api.validators.iteration_rules_validator import IterationRuleValidation


class IterationValidation(Iteration):
    @classmethod
    @field_validator("iteration_rules")
    def validate_iterations(cls, iteration_rules: list[IterationRule]) -> list[IterationRuleValidation]:
        return [IterationRuleValidation(**i.model_dump()) for i in iteration_rules]

    @classmethod
    @field_validator("actions_mapper", mode="after")
    def transform_actions_mapper(cls, action_mapper: ActionsMapper) -> ActionsMapper:
        ActionsMapperValidator.model_validate(action_mapper.model_dump())
        return action_mapper

    @model_validator(mode="after")
    def validate_default_comms_routing_in_actions_mapper(self) -> typing.Self:
        default_routing = self.default_comms_routing
        actions_mapper = self.actions_mapper.root.keys()

        if default_routing and (not actions_mapper or default_routing not in actions_mapper):
            error = InitErrorDetails(
                type="value_error",
                loc=("actions_mapper",),
                input=actions_mapper,
                ctx={"error": f"Missing entry for DefaultCommsRouting '{default_routing}' in ActionsMapper"},
            )
            raise ValidationError.from_exception_data(title="IterationValidation", line_errors=[error])

        return self
