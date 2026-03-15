"""
TagCategory domain model.
Represents a category that groups related tags together.
Fully DB-driven — no hardcoded values.
"""
import re

from pydantic import BaseModel, ConfigDict, field_validator


class TagCategory(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    slug: str
    description: str
    is_active: bool
    sort_order: int

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

    @classmethod
    def from_db(cls, row: dict) -> "TagCategory":
        return cls.model_validate(row)
