"""TaggingMode enum — controls which pipeline stages run."""

from enum import StrEnum


class TaggingMode(StrEnum):
    RULES_ONLY = "rules_only"
    LLM_ONLY = "llm_only"
    HYBRID = "hybrid"
