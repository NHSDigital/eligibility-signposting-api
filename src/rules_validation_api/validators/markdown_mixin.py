from __future__ import annotations

import logging
from typing import ClassVar, Dict, Set, Tuple
from pydantic import field_validator
from rules_validation_api.validators.markdown_lint import (
    lint_markdown_string_cli,
    MarkdownLintError,
)

logger = logging.getLogger(__name__)

class MarkdownValidatedModel:
    """Mixin: lint selected string fields as Markdown via PyMarkdown CLI."""

    # Must be ClassVar so Pydantic doesn't treat them as model fields
    MARKDOWN_FIELDS: ClassVar[Set[str]] = set()
    FIELD_DISABLE_RULES: ClassVar[Dict[str, Tuple[str, ...]]] = {}

    @field_validator("*", mode="after", check_fields=False)
    @classmethod
    def _lint_markdown_fields(cls, v, info):
        name = info.field_name
        if isinstance(v, str) and v.strip() and name in cls.MARKDOWN_FIELDS:
            try:
                lint_markdown_string_cli(
                    v,
                    name,
                    disable_rules=cls.FIELD_DISABLE_RULES.get(name, ()),
                )
                logger.debug("[Markdown] %s: OK", name)
            except MarkdownLintError as e:
                logger.warning("[Markdown] %s: FAIL: %s", name, e)
                raise ValueError(str(e)) from e
        return v
