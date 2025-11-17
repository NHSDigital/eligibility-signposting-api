from pydantic import Field, field_validator

from eligibility_signposting_api.model.campaign_config import RuleEntry, RuleText
from rules_validation_api.validators.custom_markdown_linter import validate_markdown


class RuleEntryValidation(RuleEntry):
    rule_text: RuleText | None = Field(None, alias="RuleText")

    @field_validator("rule_text")
    @classmethod
    def validate_rule_text(cls, text: str) -> str:
        if not text:
            return text
        validate_markdown(text)
        return text

