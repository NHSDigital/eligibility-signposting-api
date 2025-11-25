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
    def validate_iterations_have_unique_id(self) -> typing.Self:
        ids = [iteration.id for iteration in self.iterations]
        duplicates = {i_id for i_id, count in Counter(ids).items() if count > 1}
        if duplicates:
            raise ValueError(
                f"Iterations contain duplicate IDs: {', '.join(duplicates)}"
            )
        return self

    @model_validator(mode="after")
    def validate_campaign_has_iteration_within_schedule(self) -> typing.Self:
        iterations_by_date = sorted(self.iterations, key=attrgetter("iteration_date"))
        if first_iteration := next(iter(iterations_by_date), None):
            if first_iteration.iteration_date < self.start_date:
                raise ValueError(
                    f"Iteration {first_iteration.id} starts before campaign {self.id} "
                    f"start date {self.start_date}."
                )
            if first_iteration.iteration_date > self.end_date:
                raise ValueError(
                    f"Iteration {first_iteration.id} starts after campaign {self.id} "
                    f"end date {self.end_date}."
                )
            return self
        # Should never happen, since we are constraining self.iterations with a min_length of 1
        message = f"campaign {self.id} has no iterations."
        raise ValueError(message)
