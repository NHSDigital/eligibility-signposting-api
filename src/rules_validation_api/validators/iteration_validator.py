from pydantic import field_validator, BaseModel

from eligibility_signposting_api.model.campaign_config import Iteration

class IterationValidation(Iteration):

    @field_validator("id")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ID must not be empty")
        return value

    @field_validator("id")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ID must not be empty")
        return value


