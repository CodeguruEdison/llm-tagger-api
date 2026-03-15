"""
Unit tests for the Orchestrator.
TDD: RED before GREEN.

Orchestrator tests use MockTagRepository and mock LLM.
No DB, no real LLM calls.

Run: uv run pytest tests/unit/test_orchestrator.py -v
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tagging.application.interfaces import ITagRepository
from tagging.application.orchestrator import Orchestrator
from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.enums.tagging_mode import TaggingMode
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition


def make_tag(id="tag-1", slug="parts-delay") -> Tag:
    return Tag(
        id=id,
        category_id="cat-1",
        name="Parts Delay",
        slug=slug,
        description="Waiting on parts from supplier",
        color="#FF6B6B",
        icon="clock",
        priority=1,
        is_active=True,
    )


def make_rule(tag_id="tag-1") -> TagRule:
    return TagRule(
        id="rule-1",
        tag_id=tag_id,
        name="Parts Delay Detection",
        priority=100,
        is_enabled=True,
        conditions=[
            TagRuleCondition(
                id="cond-1",
                condition_type=ConditionType.KEYWORD_ANY,
                operator=ConditionOperator.AND,
                values=["waiting on parts"],
            )
        ],
    )


def make_context(text="waiting on parts from LKQ") -> NoteContext:
    return NoteContext(
        note_id="note-1",
        ro_id="ro-1",
        shop_id="shop-1",
        text=text,
        event_type="note",
    )


def make_mock_repo(tags=None, rules=None) -> ITagRepository:
    """Create a mock repository with controlled data."""
    repo = MagicMock(spec=ITagRepository)
    repo.get_all_active_tags = AsyncMock(return_value=tags or [])
    repo.get_all_active_rules = AsyncMock(return_value=rules or [])
    repo.save_tag_result = AsyncMock(return_value=None)
    return repo


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_rules_only_tags_note(self):
        """Orchestrator applies rules and returns results."""
        tag = make_tag()
        rule = make_rule()
        repo = make_mock_repo(tags=[tag], rules=[rule])

        orchestrator = Orchestrator(
            repository=repo,
            tagging_mode=TaggingMode.RULES_ONLY,
            llm_confidence_threshold=0.7,
        )

        results = await orchestrator.tag_note(make_context())

        assert len(results) == 1
        assert results[0].tag.slug == "parts-delay"
        assert results[0].source == TagSource.RULES

    @pytest.mark.asyncio
    async def test_saves_results_to_repository(self):
        """Each tag result is persisted via repository."""
        tag = make_tag()
        rule = make_rule()
        repo = make_mock_repo(tags=[tag], rules=[rule])

        orchestrator = Orchestrator(
            repository=repo,
            tagging_mode=TaggingMode.RULES_ONLY,
            llm_confidence_threshold=0.7,
        )

        context = make_context()
        await orchestrator.tag_note(context)

        # save_tag_result called once per matched tag
        assert repo.save_tag_result.call_count == 1
        call_args = repo.save_tag_result.call_args
        assert call_args[0][0] == context
        assert call_args[0][1].tag.slug == "parts-delay"

    @pytest.mark.asyncio
    async def test_no_match_returns_empty_and_saves_nothing(self):
        """No matches means empty results and no DB writes."""
        tag = make_tag()
        rule = make_rule()
        repo = make_mock_repo(tags=[tag], rules=[rule])

        orchestrator = Orchestrator(
            repository=repo,
            tagging_mode=TaggingMode.RULES_ONLY,
            llm_confidence_threshold=0.7,
        )

        results = await orchestrator.tag_note(
            make_context("vehicle is ready for pickup")
        )

        assert results == []
        repo.save_tag_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_loads_taxonomy_from_repository(self):
        """Orchestrator loads tags and rules from repository."""
        repo = make_mock_repo(tags=[], rules=[])

        orchestrator = Orchestrator(
            repository=repo,
            tagging_mode=TaggingMode.RULES_ONLY,
            llm_confidence_threshold=0.7,
        )

        await orchestrator.tag_note(make_context())

        repo.get_all_active_tags.assert_called_once()
        repo.get_all_active_rules.assert_called_once()
