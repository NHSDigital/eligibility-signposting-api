import re

from pydantic import field_validator

from eligibility_signposting_api.model.campaign_config import AvailableAction
from rules_validation_api.decorators.tracker import track_validators


@track_validators
class AvailableActionValidation(AvailableAction):
    @field_validator("action_description")
    @classmethod
    def validate_description_style(cls, text: str) -> str:
        if not text:
            return text
        cls.validate_markdown(text)
        return text

    @classmethod
    def validate_markdown(cls, text: str) -> None:
        errors = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            # Rule: Headers must have a space after the hash
            if re.compile(r"^#{1,6}(?![ #])").match(line) and line.strip().replace("#", "") != "":
                errors.append("Header missing space after hash (e.g., use '# Title' not '#Title').")

            # Rule: Lists must have a space after the bullet
            if re.compile(r"^(\s*)[*+-](?![ *+-])").match(line):
                errors.append("List item missing space after bullet.")

            # Rule: Headers must be surrounded by blank lines
            is_header = re.compile(r"^#{1,6} ").match(line) or re.compile(r"^#{1,6}(?![ #])").match(line)
            is_not_empty_line = i > 0 and lines[i - 1].strip() != ""
            if is_header and is_not_empty_line:
                errors.append("Header must be preceded by a blank line.")
        if errors:
            raise ValueError("\n".join(errors))
