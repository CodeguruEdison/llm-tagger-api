"""TaggingMode enum — controls which pipeline stages run."""
from enum import Enum


class TaggingMode(str, Enum):
    RULES_ONLY = "rules_only"
    LLM_ONLY = "llm_only"
    HYBRID = "hybrid"