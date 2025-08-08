import typing

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_core import InitErrorDetails

from eligibility_signposting_api.model.campaign_config import (
    ActionsMapper,
    Iteration,
    IterationCohort,
    IterationRule,
    RuleType,
)
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
    def action_mapper_validation(self) -> typing.Self:
        all_errors = []

        for validator in [
            self.validate_default_comms_routing_in_actions_mapper,
            self.validate_default_not_eligible_routing_in_actions_mapper,
            self.validate_default_not_actionable_routing_in_actions_mapper,
            self.validate_iteration_rules_against_actions_mapper,
        ]:
            try:
                validator()
            except ValidationError as ve:
                all_errors.extend(ve.errors(include_input=False))

        if all_errors:
            raise ValidationError.from_exception_data(title="IterationValidation", line_errors=all_errors)

        return self

    def validate_default_comms_routing_in_actions_mapper(self) -> typing.Self:
        default_routes = self.default_comms_routing
        actions_keys = list(self.actions_mapper.root.keys())
        line_errors = []

        for routing in default_routes.split("|"):
            cleaned_routing = routing.strip()
            if cleaned_routing and (not actions_keys or cleaned_routing not in actions_keys):
                error = InitErrorDetails(
                    type="value_error",
                    loc=("actions_mapper",),
                    input=actions_keys,
                    ctx={"error": f"Missing entry for DefaultCommsRouting '{cleaned_routing}' in ActionsMapper"},
                )
                line_errors.append(error)

        if line_errors:
            raise ValidationError.from_exception_data(title="IterationValidation", line_errors=line_errors)

        return self

    def validate_default_not_eligible_routing_in_actions_mapper(self) -> typing.Self:
        default_not_eligibile_routes = self.default_not_eligible_routing
        actions_keys = list(self.actions_mapper.root.keys())
        line_errors = []

        for routing in default_not_eligibile_routes.split("|"):
            cleaned_routing = routing.strip()
            if cleaned_routing and (not actions_keys or cleaned_routing not in actions_keys):
                error = InitErrorDetails(
                    type="value_error",
                    loc=("actions_mapper",),
                    input=actions_keys,
                    ctx={"error": f"Missing entry for DefaultNotEligibleRouting '{cleaned_routing}' in ActionsMapper"},
                )
                line_errors.append(error)

        if line_errors:
            raise ValidationError.from_exception_data(title="IterationValidation", line_errors=line_errors)

        return self

    def validate_default_not_actionable_routing_in_actions_mapper(self) -> typing.Self:
        default_not_actionable_routes = self.default_not_actionable_routing
        actions_keys = list(self.actions_mapper.root.keys())
        line_errors = []

        for routing in default_not_actionable_routes.split("|"):
            cleaned_routing = routing.strip()
            if cleaned_routing and (not actions_keys or cleaned_routing not in actions_keys):
                error = InitErrorDetails(
                    type="value_error",
                    loc=("actions_mapper",),
                    input=actions_keys,
                    ctx={
                        "error": f"Missing entry for DefaultNotActionableRouting '{cleaned_routing}' in ActionsMapper"
                    },
                )
                line_errors.append(error)

        if line_errors:
            raise ValidationError.from_exception_data(title="IterationValidation", line_errors=line_errors)

        return self

    def validate_iteration_rules_against_actions_mapper(self) -> typing.Self:
        actions_keys = list(self.actions_mapper.root.keys())
        line_errors = []

        for rule in self.iteration_rules:
            if (
                rule.type
                in [
                    RuleType.redirect,
                    RuleType.not_actionable_actions,
                    RuleType.not_eligible_actions,
                ]
                and rule.comms_routing
            ):
                for routing in rule.comms_routing.split("|"):
                    cleaned_routing = routing.strip()
                    if cleaned_routing and (not actions_keys or cleaned_routing not in actions_keys):
                        error = InitErrorDetails(
                            type="value_error",
                            loc=("iteration_rules",),
                            input=actions_keys,
                            ctx={"error": f"Missing entry for CommsRouting '{cleaned_routing}' in ActionsMapper"},
                        )
                        line_errors.append(error)

        if line_errors:
            raise ValidationError.from_exception_data(title="IterationValidation", line_errors=line_errors)

        return self
