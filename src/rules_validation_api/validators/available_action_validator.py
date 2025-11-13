from __future__ import annotations

import logging
from pydantic import field_validator
from eligibility_signposting_api.model.campaign_config import AvailableAction
from rules_validation_api.validators.markdown_lint import (
    lint_markdown_string_cli,
    MarkdownLintError,
)

logger = logging.getLogger(__name__)

MARKDOWN_FIELDS: set[str] = {"action_description"}

# Per-field rule relaxations for short snippets
FIELD_DISABLE_RULES: dict[str, tuple[str, ...]] = {
    # no “first line must be H1”, no “must end with newline”
    "action_description": ("MD041", "MD047"),
}

class AvailableActionValidation(AvailableAction):
    @field_validator("*", mode="after", check_fields=False)
    @classmethod
    def markdown_lint(cls, v, info):
        name = info.field_name
        if isinstance(v, str) and v.strip() and name in MARKDOWN_FIELDS:
            try:
                lint_markdown_string_cli(
                    v,
                    name,
                    disable_rules=FIELD_DISABLE_RULES.get(name, ()),
                )
                logger.debug("[Markdown] %s: OK", name)
            except MarkdownLintError as e:
                logger.warning("[Markdown] %s: FAIL: %s", name, e)
                raise ValueError(str(e)) from e
        return v
