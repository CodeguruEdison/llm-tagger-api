import re

from pydantic import BaseModel,ConfigDict,field_validator

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
