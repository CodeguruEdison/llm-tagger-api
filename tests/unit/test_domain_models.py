"""
Unit tests for domain models.
TDD: Tests exist before implementation.

Run: uv run pytest tests/unit/test_domain_models.py -v
Expected now: RED (ModuleNotFoundError)
"""
import pytest
from pydantic import ValidationError

from src.tagging.domain.models import TagCategory,Tag


class TestTagCategory:

    def test_can_create_category(self):
        """Basic creation works with valid data."""
        category = TagCategory(
            id="uuid-1",
            name="Parts",
            slug="parts",
            description="Parts related issues",
            is_active=True,
            sort_order=1,
        )
        assert category.name == "Parts"
        assert category.slug == "parts"
        assert category.is_active is True

    def test_slug_must_be_lowercase(self):
        """Slug must be lowercase alphanumeric with hyphens only."""
        with pytest.raises(ValidationError):
            TagCategory(
                id="uuid-1",
                name="Parts",
                slug="Parts",        # uppercase — must fail
                description="Parts related issues",
                is_active=True,
                sort_order=1,
            )

    def test_slug_no_spaces(self):
        """Slug cannot contain spaces."""
        with pytest.raises(ValidationError):
            TagCategory(
                id="uuid-1",
                name="Parts",
                slug="parts delay",  # space — must fail
                description="Parts related issues",
                is_active=True,
                sort_order=1,
            )

    def test_name_cannot_be_empty(self):
        """Empty name is meaningless in the UI."""
        with pytest.raises(ValidationError):
            TagCategory(
                id="uuid-1",
                name="",             # empty — must fail
                slug="parts",
                description="Parts related issues",
                is_active=True,
                sort_order=1,
            )

    def test_category_is_immutable(self):
        """
        Once created, a category cannot be modified.
        Why: prevents accidental mutation mid-pipeline.
        """
        category = TagCategory(
            id="uuid-1",
            name="Parts",
            slug="parts",
            description="Parts related issues",
            is_active=True,
            sort_order=1,
        )
        with pytest.raises(ValidationError):
            category.name = "Changed"  # must fail

    def test_serialize_to_dict(self):
        """
        Must serialize to dict for Redis caching.
        Why: Redis stores strings — we store JSON.
        Pydantic gives us this for free.
        """
        category = TagCategory(
            id="uuid-1",
            name="Parts",
            slug="parts",
            description="Parts related issues",
            is_active=True,
            sort_order=1,
        )
        data = category.model_dump()
        assert data["name"] == "Parts"
        assert data["slug"] == "parts"
        assert isinstance(data, dict)

    def test_deserialize_from_dict(self):
        """
        Must reconstruct from dict when reading from Redis or DB.
        Why: we store as JSON in Redis, need to rebuild the model.
        """
        data = {
            "id": "uuid-1",
            "name": "Parts",
            "slug": "parts",
            "description": "Parts related issues",
            "is_active": True,
            "sort_order": 1,
        }
        category = TagCategory.model_validate(data)
        assert category.name == "Parts"
        assert category.slug == "parts"

class TestTag:

    def test_can_create_tag(self):
        """Basic creation works with valid data."""
        tag = Tag(
            id="uuid-2",
            category_id="uuid-1",
            name="Parts Delay",
            slug="parts-delay",
            description="RO is waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )
        assert tag.name == "Parts Delay"
        assert tag.slug == "parts-delay"
        assert tag.color == "#FF6B6B"

    def test_slug_must_be_lowercase(self):
        """Slug same rules as TagCategory."""
        with pytest.raises(ValidationError):
            Tag(
                id="uuid-2",
                category_id="uuid-1",
                name="Parts Delay",
                slug="Parts-Delay",  # uppercase — must fail
                description="RO is waiting on parts",
                color="#FF6B6B",
                icon="clock",
                priority=1,
                is_active=True,
            )

    def test_color_must_be_valid_hex(self):
        """
        Color must be a valid hex color code.
        Why: stored in DB, rendered directly in UI as CSS.
        Invalid color = broken UI badge.
        """
        with pytest.raises(ValidationError):
            Tag(
                id="uuid-2",
                category_id="uuid-1",
                name="Parts Delay",
                slug="parts-delay",
                description="RO is waiting on parts",
                color="red",        # not hex — must fail
                icon="clock",
                priority=1,
                is_active=True,
            )

    def test_color_accepts_valid_hex(self):
        """Both 3 and 6 character hex codes are valid."""
        tag1 = Tag(
            id="uuid-2",
            category_id="uuid-1",
            name="Parts Delay",
            slug="parts-delay",
            description="RO is waiting on parts",
            color="#FF6B6B",        # 6 char hex ✓
            icon="clock",
            priority=1,
            is_active=True,
        )
        tag2 = Tag(
            id="uuid-3",
            category_id="uuid-1",
            name="Parts Ordered",
            slug="parts-ordered",
            description="Parts have been ordered",
            color="#F00",           # 3 char hex ✓
            icon="check",
            priority=2,
            is_active=True,
        )
        assert tag1.color == "#FF6B6B"
        assert tag2.color == "#F00"

    def test_priority_must_be_positive(self):
        """
        Priority must be >= 1.
        Why: used for display ordering.
        Zero or negative makes no sense in this context.
        """
        with pytest.raises(ValidationError):
            Tag(
                id="uuid-2",
                category_id="uuid-1",
                name="Parts Delay",
                slug="parts-delay",
                description="RO is waiting on parts",
                color="#FF6B6B",
                icon="clock",
                priority=0,         # zero — must fail
                is_active=True,
            )

    def test_tag_is_immutable(self):
        """Tags are immutable once created."""
        tag = Tag(
            id="uuid-2",
            category_id="uuid-1",
            name="Parts Delay",
            slug="parts-delay",
            description="RO is waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )
        with pytest.raises(ValidationError):
            tag.name = "Changed"

    def test_serialize_to_dict(self):
        """Must serialize to dict for Redis caching."""
        tag = Tag(
            id="uuid-2",
            category_id="uuid-1",
            name="Parts Delay",
            slug="parts-delay",
            description="RO is waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )
        data = tag.model_dump()
        assert data["name"] == "Parts Delay"
        assert data["color"] == "#FF6B6B"
        assert isinstance(data, dict)