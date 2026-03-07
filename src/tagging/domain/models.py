"""
Domain models — single entry point.

Import from here everywhere in the codebase:
  from tagging.domain.models import TagCategory, Tag, TagRule, NoteContext, TagResult
"""
from tagging.domain.tag_category import TagCategory
from tagging.domain.tag import Tag
from tagging.domain.tag_rule_condition import TagRuleCondition
from tagging.domain.tag_rule import TagRule
from tagging.domain.note_context import NoteContext
from tagging.domain.tag_result import TagResult

__all__ = [
    "TagCategory",
    "Tag",
    "TagRuleCondition",
    "TagRule",
    "NoteContext",
    "TagResult",
]