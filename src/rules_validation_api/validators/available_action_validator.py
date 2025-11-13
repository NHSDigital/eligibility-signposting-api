from __future__ import annotations

from typing import ClassVar, Dict, Set, Tuple
from eligibility_signposting_api.model.campaign_config import AvailableAction
from rules_validation_api.markdown.markdown_mixin import MarkdownValidatedModel

class AvailableActionValidation(AvailableAction, MarkdownValidatedModel):
    MARKDOWN_FIELDS: ClassVar[Set[str]] = {"action_description"}
    FIELD_DISABLE_RULES: ClassVar[Dict[str, Tuple[str, ...]]] = {
        "action_description": ("MD041", "MD047", "MD013"),
    }
