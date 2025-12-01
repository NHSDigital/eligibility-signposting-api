import typing
from collections import Counter
from operator import attrgetter

from pydantic import field_validator, model_validator

from eligibility_signposting_api.model.campaign_config import CampaignConfig, Iteration
from rules_validation_api.validators.iteration_validator import IterationValidation


class CampaignConfigValidation(CampaignConfig):
    @field_validator("iterations")
    @classmethod
    def validate_iterations(cls, iterations: list[Iteration]) -> list[IterationValidation]:
        return [IterationValidation(**i.model_dump()) for i in iterations]

    @model_validator(mode="after")
    def validate_approval_minimum_is_less_than_or_equal_to_approval_maximum(self) -> typing.Self:
        if self.approval_minimum is not None and self.approval_maximum is not None:
            if self.approval_minimum > self.approval_maximum:
                msg = f"approval_minimum {self.approval_minimum} > approval_maximum {self.approval_maximum}"
                raise ValueError(msg)
            return self
        return self

    @model_validator(mode="after")
    def validate_iterations_have_unique_id(self) -> typing.Self:
        ids = [iteration.id for iteration in self.iterations]
        duplicates = {i_id for i_id, count in Counter(ids).items() if count > 1}
        if duplicates:
            msg = f"Iterations contain duplicate IDs: {', '.join(duplicates)}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_campaign_has_iteration_within_schedule(self) -> typing.Self:
        errors: list[str] = []
        iterations_by_date = sorted(self.iterations, key=attrgetter("iteration_date"))

        for iteration in iterations_by_date:
            if iteration.iteration_date < self.start_date:
                errors.append(
                    f"\nIteration {iteration.id} starts before campaign {self.id} start date {self.start_date}."
                )
            if iteration.iteration_date > self.end_date:
                errors.append(f"\nIteration {iteration.id} starts after campaign {self.id} end date {self.end_date}.")

        if errors:
            # Raise one exception with all messages joined
            raise ValueError("".join(errors))

        return self
