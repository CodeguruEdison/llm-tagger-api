"""
Unit tests for domain models.
TDD: Tests exist before implementation.

Run: uv run pytest tests/unit/test_domain_models.py -v
Expected now: RED (ModuleNotFoundError)
"""
import pytest
from pydantic import ValidationError

from tagging.domain.models import TagCategory


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
