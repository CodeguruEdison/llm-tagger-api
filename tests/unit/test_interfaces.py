"""
Unit tests for ITagRepository interface.

We test that:
  - Interface cannot be instantiated directly
  - All abstract methods are defined
  - Mock implementation satisfies the contract

Run: uv run pytest tests/unit/test_interfaces.py -v --no-cov
Expected: GREEN (interface + mock are pure Python, no DB needed)
"""
import pytest

from tagging.application.interfaces import ITagRepository
from tagging.domain.tag_category import TagCategory
from tagging.domain.tag import Tag
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_result import TagResult
from tagging.domain.note_context import NoteContext
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.tag_rule_condition import TagRuleCondition


class MockTagRepository(ITagRepository):
    """
    In-memory implementation of ITagRepository.
    Used in tests — no DB, no Docker, runs in milliseconds.
    """

    def __init__(self):
        self._categories: list[TagCategory] = []
        self._tags: list[Tag] = []
        self._rules: list[TagRule] = []
        self._results: list[tuple[NoteContext, TagResult]] = []

    async def get_all_categories(self) -> list[TagCategory]:
        return self._categories

    async def get_tags_by_category(self, category_id: str) -> list[Tag]:
        return [t for t in self._tags if t.category_id == category_id]

    async def get_all_active_tags(self) -> list[Tag]:
        return [t for t in self._tags if t.is_active]

    async def get_rules_for_tag(self, tag_id: str) -> list[TagRule]:
        return [r for r in self._rules if r.tag_id == tag_id]

    async def get_all_active_rules(self) -> list[TagRule]:
        return [r for r in self._rules if r.is_enabled]

    async def save_tag_result(
        self, context: NoteContext, result: TagResult
    ) -> None:
        self._results.append((context, result))

    async def get_results_for_note(
        self, note_id: str
    ) -> list[TagResult]:
        return [
            result
            for context, result in self._results
            if context.note_id == note_id
        ]


class TestITagRepository:

    def test_cannot_instantiate_interface_directly(self):
        """
        Interface is abstract — cannot be used directly.
        Must be implemented by a concrete class.
        """
        with pytest.raises(TypeError):
            ITagRepository()

    @pytest.mark.asyncio
    async def test_mock_get_all_categories(self):
        """Mock returns categories correctly."""
        repo = MockTagRepository()
        repo._categories = [
            TagCategory(
                id="cat-1",
                name="Parts",
                slug="parts",
                description="Parts issues",
                is_active=True,
                sort_order=1,
            )
        ]
        result = await repo.get_all_categories()
        assert len(result) == 1
        assert result[0].name == "Parts"

    @pytest.mark.asyncio
    async def test_mock_get_tags_by_category(self):
        """Mock filters tags by category_id correctly."""
        repo = MockTagRepository()
        repo._tags = [
            Tag(
                id="tag-1",
                category_id="cat-1",
                name="Parts Delay",
                slug="parts-delay",
                description="Waiting on parts",
                color="#FF6B6B",
                icon="clock",
                priority=1,
                is_active=True,
            ),
            Tag(
                id="tag-2",
                category_id="cat-2",  # different category
                name="Customer Concern",
                slug="customer-concern",
                description="Customer issue",
                color="#3B82F6",
                icon="user",
                priority=1,
                is_active=True,
            ),
        ]
        result = await repo.get_tags_by_category("cat-1")
        assert len(result) == 1
        assert result[0].name == "Parts Delay"

    @pytest.mark.asyncio
    async def test_mock_save_and_retrieve_result(self):
        """Mock saves and retrieves tag results correctly."""
        repo = MockTagRepository()

        context = NoteContext(
            note_id="note-1",
            ro_id="ro-1",
            shop_id="shop-1",
            text="waiting on parts",
            event_type="note",
        )
        tag = Tag(
            id="tag-1",
            category_id="cat-1",
            name="Parts Delay",
            slug="parts-delay",
            description="Waiting on parts",
            color="#FF6B6B",
            icon="clock",
            priority=1,
            is_active=True,
        )
        result = TagResult(
            tag=tag,
            confidence=1.0,
            source=TagSource.RULES,
            reasoning="matched rule: Parts Delay Detection",
        )

        await repo.save_tag_result(context, result)
        retrieved = await repo.get_results_for_note("note-1")

        assert len(retrieved) == 1
        assert retrieved[0].tag.name == "Parts Delay"

    @pytest.mark.asyncio
    async def test_mock_get_all_active_rules(self):
        """Mock returns only enabled rules."""
        repo = MockTagRepository()
        repo._rules = [
            TagRule(
                id="rule-1",
                tag_id="tag-1",
                name="Active Rule",
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
            ),
            TagRule(
                id="rule-2",
                tag_id="tag-1",
                name="Disabled Rule",
                priority=90,
                is_enabled=False,   # disabled
                conditions=[
                    TagRuleCondition(
                        id="cond-2",
                        condition_type=ConditionType.KEYWORD_ANY,
                        operator=ConditionOperator.AND,
                        values=["waiting"],
                    )
                ],
            ),
        ]
        result = await repo.get_all_active_rules()
        assert len(result) == 1
        assert result[0].name == "Active Rule"