import typing
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
    def check_has_iteration_from_start(self) -> typing.Self:
        iterations_by_date = sorted(self.iterations, key=attrgetter("iteration_date"))
        if first_iteration := next(iter(iterations_by_date), None):
            if first_iteration.iteration_date > self.start_date:
                message = (
                    f"campaign {self.id} starts on {self.start_date}, "
                    f"1st iteration starts later - {first_iteration.iteration_date}"
                )
                raise ValueError(message)
            return self
        # Should never happen, since we are constraining self.iterations with a min_length of 1
        message = f"campaign {self.id} has no iterations."
        raise ValueError(message)
