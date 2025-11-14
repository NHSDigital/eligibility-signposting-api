from pydantic import ValidationError, model_validator

from eligibility_signposting_api.model.campaign_config import ActionsMapper
from rules_validation_api.validators.available_action_validator import AvailableActionValidation


class ActionsMapperValidation(ActionsMapper):
    @model_validator(mode="after")
    def validate_keys(self) -> "ActionsMapperValidation":
        invalid_keys = [key for key in self.root if key is None or key == ""]
        if invalid_keys:
            msg = f"Invalid keys found in ActionsMapper: {invalid_keys}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_values(self) -> "ActionsMapperValidation":
        error_report = []

        for key, value in self.root.items():
            try:
                AvailableActionValidation.model_validate(value.model_dump())
            except ValidationError as e:
                for err in e.errors():
                    msg = err.get("msg", "Unknown error").replace("Value error, ", "")
                    error_report.append(f"\n❌ Action '{key}': {msg}")

        if error_report:
            final_msg = "Markdown Validation Issues:".join(error_report)
            raise ValueError(final_msg)

        return self
