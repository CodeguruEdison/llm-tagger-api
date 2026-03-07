"""Unit tests for Tag domain model."""
import pytest
from pydantic import ValidationError

from tagging.domain.tag import Tag


class TestTag:

    def _make_tag(self, **overrides) -> Tag:
        """Helper — avoids repeating valid tag data in every test."""
        defaults = dict(
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
        return Tag(**{**defaults, **overrides})

    def test_can_create_tag(self):
        tag = self._make_tag()
        assert tag.name == "Parts Delay"
        assert tag.slug == "parts-delay"
        assert tag.color == "#FF6B6B"

    def test_slug_must_be_lowercase(self):
        with pytest.raises(ValidationError):
            self._make_tag(slug="Parts-Delay")

    def test_color_must_be_valid_hex(self):
        with pytest.raises(ValidationError):
            self._make_tag(color="red")

    def test_color_accepts_six_char_hex(self):
        tag = self._make_tag(color="#FF6B6B")
        assert tag.color == "#FF6B6B"

    def test_color_accepts_three_char_hex(self):
        tag = self._make_tag(color="#F00")
        assert tag.color == "#F00"

    def test_priority_must_be_positive(self):
        with pytest.raises(ValidationError):
            self._make_tag(priority=0)

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            self._make_tag(name="")

    def test_tag_is_immutable(self):
        tag = self._make_tag()
        with pytest.raises(ValidationError):
            tag.name = "Changed"

    def test_serialize_to_dict(self):
        tag = self._make_tag()
        data = tag.model_dump()
        assert data["name"] == "Parts Delay"
        assert data["color"] == "#FF6B6B"
        assert isinstance(data, dict)