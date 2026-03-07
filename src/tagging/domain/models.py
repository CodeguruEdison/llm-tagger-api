"""
Domain models — single entry point.

Import from here everywhere in the codebase:
  from tagging.domain.models import TagCategory, Tag, TagRule

This keeps imports clean and lets us reorganize
internal files without touching every consumer.
"""
from tagging.domain.tag_category import TagCategory
from tagging.domain.tag import Tag
from tagging.domain.tag_rule_condition import TagRuleCondition
from tagging.domain.tag_rule import TagRule

__all__ = [
    "TagCategory",
    "Tag",
    "TagRuleCondition",
    "TagRule",
]