"""
Tag domain model.
Represents a label applied to a note or event.
Belongs to a TagCategory.
"""
import re

from pydantic import BaseModel, ConfigDict, field_validator


class Tag(BaseModel):
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
        return cls.model_validate(row)
