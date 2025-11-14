import re

import markdown
from pydantic import field_validator, Field

from eligibility_signposting_api.model.campaign_config import AvailableAction


class AvailableActionValidation(AvailableAction):
    action_description: str | None = Field(None, alias="ActionDescription")

    @field_validator("action_description")
    @classmethod
    def validate_description_style(cls, text: str) -> str:
        if not text:
            return text
        cls.validate_markdown(text)
        return text

    @classmethod
    def validate_markdown(cls, text: str) -> None:
        try:
            markdown.markdown(text)
        except Exception as e:
            raise ValueError(f"Critical Markdown syntax error: {str(e)}")

        errors = []
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Rule: Headers must have a space after the hash
            if re.compile(r'^#{1,6}(?![ #])').match(line):
                if line.strip().replace('#', '') != '':
                    errors.append(f"Header missing space after hash (e.g., use '# Title' not '#Title').")

            # Rule: Lists must have a space after the bullet
            if re.compile(r'^(\s*)[*+-](?![ *+-])').match(line):
                errors.append(f"List item missing space after bullet.")

            # Rule: Headers must be surrounded by blank lines
            if re.compile(r'^#{1,6} ').match(line) or re.compile(r'^#{1,6}(?![ #])').match(line):
                if i > 0 and lines[i - 1].strip() != "":
                    errors.append(f"Header must be preceded by a blank line.")
        if errors:
            raise ValueError("\n".join(errors))
