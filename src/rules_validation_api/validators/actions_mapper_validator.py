from pydantic import model_validator

from eligibility_signposting_api.model.campaign_config import ActionsMapper


class ActionsMapperValidation(ActionsMapper):
    @model_validator(mode="after")
    def validate_keys(self) -> "ActionsMapperValidation":
        invalid_keys = [key for key in self.root if key is None or key == ""]
        if invalid_keys:
            msg = f"Invalid keys found in ActionsMapper: {invalid_keys}"
            raise ValueError(msg)
        return self
