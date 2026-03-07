"""Unit tests for TagCategory domain model."""
import pytest
from pydantic import ValidationError

from tagging.domain.tag_category import TagCategory


class TestTagCategory:

    def test_can_create_category(self):
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
        with pytest.raises(ValidationError):
            TagCategory(
                id="uuid-1",
                name="Parts",
                slug="Parts",
                description="Parts related issues",
                is_active=True,
                sort_order=1,
            )

    def test_slug_no_spaces(self):
        with pytest.raises(ValidationError):
            TagCategory(
                id="uuid-1",
                name="Parts",
                slug="parts delay",
                description="Parts related issues",
                is_active=True,
                sort_order=1,
            )

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            TagCategory(
                id="uuid-1",
                name="",
                slug="parts",
                description="Parts related issues",
                is_active=True,
                sort_order=1,
            )

    def test_category_is_immutable(self):
        category = TagCategory(
            id="uuid-1",
            name="Parts",
            slug="parts",
            description="Parts related issues",
            is_active=True,
            sort_order=1,
        )
        with pytest.raises(ValidationError):
            category.name = "Changed"

    def test_serialize_to_dict(self):
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