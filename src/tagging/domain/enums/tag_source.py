"""TagSource enum — which part of pipeline applied the tag."""
from enum import StrEnum


class TagSource(StrEnum):
    RULES = "rules"
    LLM = "llm"
