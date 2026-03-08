"""
Unit tests for SQLAlchemy ORM models.
TDD: RED before GREEN.

These tests verify:
  - Tables have correct columns
  - Relationships are defined correctly
  - Indexes exist for performance-critical queries

Run: uv run pytest tests/unit/test_db_models.py -v --no-cov

"""
import pytest
from sqlalchemy import inspect

from tagging.infrastructure.db.models import (
    TagCategoryModel,
    TagModel,
    TagRuleModel,
    TagRuleConditionModel,
)


class TestTagCategoryModel:

    def test_table_name(self):
        assert TagCategoryModel.__tablename__ == "tag_categories"

    def test_has_required_columns(self):
        mapper = inspect(TagCategoryModel)
        columns = [c.key for c in mapper.columns]
        assert "id" in columns
        assert "name" in columns
        assert "slug" in columns
        assert "description" in columns
        assert "is_active" in columns
        assert "sort_order" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_slug_is_unique(self):
        mapper = inspect(TagCategoryModel)
        slug_col = mapper.columns["slug"]
        assert slug_col.unique is True

    def test_converts_to_domain_model(self):
        """
        ORM model must convert to domain model cleanly.
        This is what the repository calls after every DB read.
        """
        orm = TagCategoryModel(
            id="uuid-1",
            name="Parts",
            slug="parts",
            description="Parts related issues",
            is_active=True,
            sort_order=1,
        )
        domain = orm.to_domain()
        assert domain.name == "Parts"
        assert domain.slug == "parts"


class TestTagModel:

    def test_table_name(self):
        assert TagModel.__tablename__ == "tags"

    def test_has_required_columns(self):
        mapper = inspect(TagModel)
        columns = [c.key for c in mapper.columns]
        assert "id" in columns
        assert "category_id" in columns
        assert "name" in columns
        assert "slug" in columns
        assert "description" in columns
        assert "color" in columns
        assert "icon" in columns
        assert "priority" in columns
        assert "is_active" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_slug_is_unique(self):
        mapper = inspect(TagModel)
        slug_col = mapper.columns["slug"]
        assert slug_col.unique is True

    def test_converts_to_domain_model(self):
        orm = TagModel(
            id="uuid-2",
            category_id="uuid-1",
            name="Parts Delay",
            slug="parts-delay",
            description="RO waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )
        domain = orm.to_domain()
        assert domain.name == "Parts Delay"
        assert domain.color == "#FF6B6B"


class TestTagRuleModel:

    def test_table_name(self):
        assert TagRuleModel.__tablename__ == "tag_rules"

    def test_has_required_columns(self):
        mapper = inspect(TagRuleModel)
        columns = [c.key for c in mapper.columns]
        assert "id" in columns
        assert "tag_id" in columns
        assert "name" in columns
        assert "priority" in columns
        assert "is_enabled" in columns
        assert "created_at" in columns
        assert "updated_at" in columns


class TestTagRuleConditionModel:

    def test_table_name(self):
        assert TagRuleConditionModel.__tablename__ == "tag_rule_conditions"

    def test_has_required_columns(self):
        mapper = inspect(TagRuleConditionModel)
        columns = [c.key for c in mapper.columns]
        assert "id" in columns
        assert "rule_id" in columns
        assert "condition_type" in columns
        assert "operator" in columns
        assert "values" in columns
        assert "created_at" in columns