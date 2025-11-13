from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from pydantic import field_validator
from eligibility_signposting_api.model.campaign_config import AvailableAction
from rules_validation_api.validators.markdown_lint import (
    lint_markdown_string_cli,
    MarkdownLintError,
)

# Adjust to the actual text fields in your AvailableAction model:
_MARKDOWN_FIELDS = (
    "action_description",
)

# Optional: central place to tweak rules, e.g. disable long-line (MD013) or trailing newline (MD047)
_CLI_EXTRA_ARGS: tuple[str, ...] = ( "-d", "MD041", "-d", "MD047"
)


class AvailableActionValidation(AvailableAction):
    @field_validator("*", mode="after", check_fields=False)
    @classmethod
    def validate_markdown_fields(cls, v, info):
        name = info.field_name

        # log what the validator *sees*
        if isinstance(v, str):
            logger.debug(f"[MarkdownCheck] field='{name}' len={len(v)} selected={name in _MARKDOWN_FIELDS}")
        else:
            logger.debug(f"[MarkdownCheck] field='{name}' type={type(v).__name__} (not a str) — skipping")

        # reasons to skip
        if not isinstance(v, str):
            return v
        if not v.strip():
            logger.debug(f"[MarkdownCheck] field='{name}' empty/whitespace — skipping")
            return v
        if name not in _MARKDOWN_FIELDS:
            logger.debug(f"[MarkdownCheck] field='{name}' not in _MARKDOWN_FIELDS — skipping")
            return v

        # run lint
        try:
            logger.debug(f"[MarkdownCheck] LINT field='{name}' preview={v[:80]!r}")
            lint_markdown_string_cli(v, name, _CLI_EXTRA_ARGS)
            logger.info(f"[MarkdownCheck] field='{name}' ✅ passed markdown validation")
        except MarkdownLintError as e:
            logger.warning(f"[MarkdownCheck] field='{name}' ❌ failed: {e}")
            raise ValueError(str(e)) from e

        return v
