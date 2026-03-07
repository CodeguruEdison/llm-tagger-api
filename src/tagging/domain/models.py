import re

from pydantic import BaseModel, ConfigDict, field_validator

from tagging.domain.enums import ConditionOperator, ConditionType

class TagCategory(BaseModel):
    """
    Represents a category that groups related tags.

    Fully DB-driven — no hardcoded values anywhere.
    UI manages creation, editing, deactivation.
    Redis caches the full taxonomy for fast reads.

    model_config frozen=True means immutable after creation.
    Same safety as dataclass(frozen=True) but with
    all Pydantic benefits on top.
    """
    model_config = ConfigDict(frozen=True)
    id:str
    name:str
    slug:str
    description:str
    is_active:bool
    sort_order: int

    @field_validator("name")
    @classmethod
    def name_cannot_be_empty(cls,v:str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()
    @field_validator("slug")
    @classmethod
    def slug_must_be_valid(cls,v:str) -> str:
        """
            Slug rules:
            - lowercase only
            - alphanumeric and hyphens only
            - no spaces, no uppercase, no special chars

            Why so strict:
            slug is used as:
                1. Redis cache key prefix  → taxonomy:parts:tags
                2. API filter parameter    → GET /ros?category=parts
                3. PostgreSQL VARCHAR      → consistent querying
            Any inconsistency here creates hard-to-find bugs at scale.
        """
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError(
                "slug must be lowercase alphanumeric with hyphens only. "
                f"Got: '{v}'"
            )
        return v

    @classmethod
    def from_db(cls, row: dict) -> "TagCategory":
        """
        Convenience method to reconstruct from a DB row.
        Why: makes the repository layer cleaner.
        Instead of:
        TagCategory.model_validate(dict(row))
        We write:
        TagCategory.from_db(row)
        Reads like English. Clear intent.
        """
        return cls.model_validate(row)
class Tag(BaseModel):
    """
    Represents a label applied to a note or event.

    Belongs to a TagCategory.
    Applied by rules engine or LLM chain.
    Displayed as colored badge in UI.

    Examples:
      Category: Parts  →  Tag: Parts Delay
      Category: Customer  →  Tag: Customer Concern
    """
    model_config = ConfigDict(frozen=True)

    id: str
    category_id: str
    name: str
    slug: str
    description: str
    color: str
    icon: str
    priority: int
    is_active: bool

    @field_validator("name")
    @classmethod
    def name_cannot_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("slug")
    @classmethod
    def slug_must_be_valid(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError(
                "slug must be lowercase alphanumeric with hyphens only. "
                f"Got: '{v}'"
            )
        return v

    @field_validator("color")
    @classmethod
    def color_must_be_valid_hex(cls, v: str) -> str:
        """
        Validates CSS hex color codes.
        Accepts: #FF6B6B (6 char) or #F00 (3 char)
        Rejects: 'red', 'FF6B6B' (no hash), '#GGGGGG' (invalid hex)

        Why: color is rendered directly as CSS in the UI.
        Invalid value = broken badge color = poor UX.
        """
        if not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', v):
            raise ValueError(
                "color must be a valid hex code like #FF6B6B or #F00. "
                f"Got: '{v}'"
            )
        return v

    @field_validator("priority")
    @classmethod
    def priority_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("priority must be >= 1")
        return v

    @classmethod
    def from_db(cls, row: dict) -> "Tag":
        """Reconstruct from a DB row."""
        return cls.model_validate(row)


class TagRuleCondition(BaseModel):
    """
    A single matching condition within a TagRule.

    condition_type: how to match (keyword, phrase, regex)
    operator:       how this condition combines with others (AND/OR)
    values:         the keywords/phrases/patterns to match against
    """
    model_config = ConfigDict(frozen=True)

    id: str
    condition_type: ConditionType
    operator: ConditionOperator
    values: list[str]

    @field_validator("values")
    @classmethod
    def values_cannot_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("values cannot be empty — a condition with no values can never match")
        return v


class TagRule(BaseModel):
    """
    A rule that maps conditions to a Tag.

    When all/any conditions pass (per operator), the tag is applied.
    Rules are evaluated in priority order (highest first).
    """
    model_config = ConfigDict(frozen=True)

    id: str
    tag_id: str
    name: str
    priority: int
    is_enabled: bool
    conditions: list[TagRuleCondition]

    @field_validator("priority")
    @classmethod
    def priority_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("priority must be >= 1")
        return v

    @field_validator("conditions")
    @classmethod
    def must_have_at_least_one_condition(cls, v: list[TagRuleCondition]) -> list[TagRuleCondition]:
        if not v:
            raise ValueError("a rule must have at least one condition")
        return v
