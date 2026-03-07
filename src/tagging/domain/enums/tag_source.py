"""TagSource enum — which part of pipeline applied the tag."""
from enum import Enum


class TagSource(str, Enum):
    RULES = "rules"
    LLM = "llm"