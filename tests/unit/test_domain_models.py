"""
Unit tests for domain models.
TDD: Tests exist before implementation.

Run: uv run pytest tests/unit/test_domain_models.py -v
Expected now: RED (ModuleNotFoundError)
"""
import pytest
from pydantic import ValidationError

from src.tagging.domain.models import TagCategory,Tag
from src.tagging.domain.models import TagCategory, Tag, TagRule, TagRuleCondition
from src.tagging.domain.enums import ConditionType, ConditionOperator



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


class TestTagRuleCondition:

    def test_can_create_condition(self):
        """Basic condition creation works."""
        condition = TagRuleCondition(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered", "waiting on parts"],
        )
        assert condition.condition_type == ConditionType.KEYWORD_ANY
        assert len(condition.values) == 2

    def test_values_cannot_be_empty(self):
        """A condition with no values can never match anything."""
        with pytest.raises(ValidationError):
            TagRuleCondition(
                id="cond-1",
                condition_type=ConditionType.KEYWORD_ANY,
                operator=ConditionOperator.AND,
                values=[],          # empty — must fail
            )

    def test_condition_is_immutable(self):
        """Conditions are immutable once created."""
        condition = TagRuleCondition(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered"],
        )
        with pytest.raises(ValidationError):
            condition.values = ["changed"]


class TestTagRule:

    def test_can_create_rule(self):
        """Basic rule creation works."""
        rule = TagRule(
            id="rule-1",
            tag_id="uuid-2",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered", "waiting on parts"],
                )
            ],
        )
        assert rule.name == "Parts Delay Detection"
        assert rule.priority == 100
        assert len(rule.conditions) == 1

    def test_rule_must_have_at_least_one_condition(self):
        """
        A rule with no conditions would match every single note.
        That would tag everything — useless and dangerous.
        """
        with pytest.raises(ValidationError):
            TagRule(
                id="rule-1",
                tag_id="uuid-2",
                name="Parts Delay Detection",
                priority=100,
                is_enabled=True,
                conditions=[],      # empty — must fail
            )

    def test_priority_must_be_positive(self):
        """Priority must be >= 1."""
        with pytest.raises(ValidationError):
            TagRule(
                id="rule-1",
                tag_id="uuid-2",
                name="Parts Delay Detection",
                priority=0,         # zero — must fail
                is_enabled=True,
                conditions=[
                    TagRuleCondition(
                        id="cond-1",
                        condition_type=ConditionType.KEYWORD_ANY,
                        operator=ConditionOperator.AND,
                        values=["backordered"],
                    )
                ],
            )

    def test_rule_is_immutable(self):
        """Rules are immutable once created."""
        rule = TagRule(
            id="rule-1",
            tag_id="uuid-2",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered"],
                )
            ],
        )
        with pytest.raises(ValidationError):
            rule.name = "Changed"



class TestTagRuleCondition:

    def test_can_create_condition(self):
        """Basic condition creation works."""
        condition = TagRuleCondition(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered", "waiting on parts"],
        )
        assert condition.condition_type == ConditionType.KEYWORD_ANY
        assert len(condition.values) == 2

    def test_values_cannot_be_empty(self):
        """
        A condition with no values can never match anything.
        Useless condition = bug waiting to happen.
        """
        with pytest.raises(ValidationError):
            TagRuleCondition(
                id="cond-1",
                condition_type=ConditionType.KEYWORD_ANY,
                operator=ConditionOperator.AND,
                values=[],          # empty — must fail
            )

    def test_condition_is_immutable(self):
        """Conditions cannot be modified after creation."""
        condition = TagRuleCondition(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered"],
        )
        with pytest.raises(ValidationError):
            condition.values = ["changed"]

    def test_serialize_to_dict(self):
        """Must serialize for Redis caching."""
        condition = TagRuleCondition(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered"],
        )
        data = condition.model_dump()
        assert data["condition_type"] == "keyword_any"
        assert data["values"] == ["backordered"]


class TestTagRule:

    def _make_condition(self) -> TagRuleCondition:
        """Helper to create a valid condition."""
        return TagRuleCondition(
            id="cond-1",
            condition_type=ConditionType.KEYWORD_ANY,
            operator=ConditionOperator.AND,
            values=["backordered", "waiting on parts"],
        )

    def test_can_create_rule(self):
        """Basic rule creation works."""
        rule = TagRule(
            id="rule-1",
            tag_id="uuid-2",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=[self._make_condition()],
        )
        assert rule.name == "Parts Delay Detection"
        assert rule.priority == 100
        assert len(rule.conditions) == 1

    def test_rule_must_have_at_least_one_condition(self):
        """
        A rule with no conditions matches every note.
        That would tag everything — catastrophic at scale.
        Imagine 1M notes all getting wrong tags.
        """
        with pytest.raises(ValidationError):
            TagRule(
                id="rule-1",
                tag_id="uuid-2",
                name="Parts Delay Detection",
                priority=100,
                is_enabled=True,
                conditions=[],      # empty — must fail
            )

    def test_priority_must_be_positive(self):
        """Priority must be >= 1."""
        with pytest.raises(ValidationError):
            TagRule(
                id="rule-1",
                tag_id="uuid-2",
                name="Parts Delay Detection",
                priority=0,         # zero — must fail
                is_enabled=True,
                conditions=[self._make_condition()],
            )

    def test_name_cannot_be_empty(self):
        """Rule name shown in admin UI — cannot be empty."""
        with pytest.raises(ValidationError):
            TagRule(
                id="rule-1",
                tag_id="uuid-2",
                name="",            # empty — must fail
                priority=100,
                is_enabled=True,
                conditions=[self._make_condition()],
            )

    def test_rule_is_immutable(self):
        """Rules are immutable once created."""
        rule = TagRule(
            id="rule-1",
            tag_id="uuid-2",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=[self._make_condition()],
        )
        with pytest.raises(ValidationError):
            rule.name = "Changed"

    def test_rule_with_multiple_conditions(self):
        """
        A rule can have multiple conditions.
        Real world example:
          Condition 1: contains "backordered" (KEYWORD_ANY)
          Condition 2: NOT contains "parts arrived" (KEYWORD_NONE)
        Both must pass for Parts Delay to be applied.
        """
        rule = TagRule(
            id="rule-1",
            tag_id="uuid-2",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=[
                TagRuleCondition(
                    id="cond-1",
                    condition_type=ConditionType.KEYWORD_ANY,
                    operator=ConditionOperator.AND,
                    values=["backordered", "waiting on parts"],
                ),
                TagRuleCondition(
                    id="cond-2",
                    condition_type=ConditionType.KEYWORD_NONE,
                    operator=ConditionOperator.AND,
                    values=["parts arrived", "parts received"],
                ),
            ],
        )
        assert len(rule.conditions) == 2

    def test_serialize_to_dict(self):
        """Must serialize including nested conditions."""
        rule = TagRule(
            id="rule-1",
            tag_id="uuid-2",
            name="Parts Delay Detection",
            priority=100,
            is_enabled=True,
            conditions=[self._make_condition()],
        )
        data = rule.model_dump()
        assert data["name"] == "Parts Delay Detection"
        assert data["priority"] == 100
        assert len(data["conditions"]) == 1
        assert data["conditions"][0]["values"] == [
            "backordered",
            "waiting on parts",
        ]