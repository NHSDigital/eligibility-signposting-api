import re

from pydantic import Field, field_validator

from eligibility_signposting_api.model.campaign_config import AvailableAction
from rules_validation_api.validators.custom_markdown_linter import validate_markdown


class AvailableActionValidation(AvailableAction):
    action_description: str | None = Field(None, alias="ActionDescription")

    @field_validator("action_description")
    @classmethod
    def validate_description_style(cls, text: str) -> str:
        if not text:
            return text
        validate_markdown(text)
        return text
