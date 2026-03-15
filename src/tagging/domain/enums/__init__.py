"""
Domain enums — single entry point.

Import from here everywhere:
  from tagging.domain.enums import LLMProvider, TaggingMode
"""

from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.llm_provider import LLMProvider
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.enums.tagging_mode import TaggingMode

__all__ = [
    "ConditionType",
    "ConditionOperator",
    "TaggingMode",
    "TagSource",
    "LLMProvider",
]
