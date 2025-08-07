import typing

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_core import InitErrorDetails

from eligibility_signposting_api.model.campaign_config import ActionsMapper, Iteration, IterationCohort, IterationRule
from rules_validation_api.validators.actions_mapper_validator import ActionsMapperValidation
from rules_validation_api.validators.iteration_cohort_validator import IterationCohortValidation
from rules_validation_api.validators.iteration_rules_validator import IterationRuleValidation


class IterationValidation(Iteration):
    iteration_cohorts: list[IterationCohort] = Field(..., alias="IterationCohorts")
    iteration_rules: list[IterationRule] = Field(..., alias="IterationRules")
    actions_mapper: ActionsMapper = Field(..., alias="ActionsMapper")

    @field_validator("iteration_rules")
    @classmethod
    def validate_iteration_rules(cls, iteration_rules: list[IterationRule]) -> list[IterationRuleValidation]:
        return [IterationRuleValidation(**i.model_dump()) for i in iteration_rules]

    @field_validator("iteration_cohorts")
    @classmethod
    def validate_iteration_cohorts(cls, iteration_cohorts: list[IterationCohort]) -> list[IterationCohortValidation]:
        return [IterationCohortValidation(**i.model_dump()) for i in iteration_cohorts]

    @field_validator("actions_mapper", mode="after")
    @classmethod
    def transform_actions_mapper(cls, action_mapper: ActionsMapper) -> ActionsMapper:
        ActionsMapperValidation.model_validate(action_mapper.model_dump())
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
