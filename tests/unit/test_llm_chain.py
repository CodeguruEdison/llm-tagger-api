"""
Unit tests for LLM chain.
TDD: RED before GREEN.

All tests use mocked LLM — no real API calls.

Run: uv run pytest tests/unit/test_llm_chain.py -v
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from tagging.domain.enums.tag_source import TagSource
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.infrastructure.llm.chain import LLMChain


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


def make_context() -> NoteContext:
    return NoteContext(
        note_id="note-1",
        ro_id="ro-1",
        shop_id="shop-1",
        text="waiting on parts from LKQ",
        event_type="note",
    )


class TestLLMChain:

    def _make_llm(self, response: str):
        """Create a mock LLM that returns a fixed response."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=AIMessage(content=response)
        )
        return llm

    @pytest.mark.asyncio
    async def test_returns_tag_results(self):
        """Chain parses LLM JSON and returns TagResult list."""
        llm = self._make_llm(
            '[{"tag_slug": "parts-delay", "confidence": 0.95, "reasoning": "waiting on parts mentioned"}]'
        )
        chain = LLMChain(llm=llm)
        results = await chain.run(
            context=make_context(),
            tags=[make_tag()],
            threshold=0.7,
        )
        assert len(results) == 1
        assert results[0].tag.slug == "parts-delay"
        assert results[0].confidence == 0.95
        assert results[0].source == TagSource.LLM

    @pytest.mark.asyncio
    async def test_empty_array_returns_no_results(self):
        """LLM returning [] means no tags apply."""
        llm = self._make_llm("[]")
        chain = LLMChain(llm=llm)
        results = await chain.run(
            context=make_context(),
            tags=[make_tag()],
            threshold=0.7,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_ignores_unknown_slug(self):
        """LLM hallucinating unknown slug is silently ignored."""
        llm = self._make_llm(
            '[{"tag_slug": "made-up-tag", "confidence": 0.9, "reasoning": "test"}]'
        )
        chain = LLMChain(llm=llm)
        results = await chain.run(
            context=make_context(),
            tags=[make_tag()],
            threshold=0.7,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_ignores_results_below_threshold(self):
        """Results below confidence threshold are filtered out."""
        llm = self._make_llm(
            '[{"tag_slug": "parts-delay", "confidence": 0.5, "reasoning": "test"}]'
        )
        chain = LLMChain(llm=llm)
        results = await chain.run(
            context=make_context(),
            tags=[make_tag()],
            threshold=0.7,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_handles_invalid_json_gracefully(self):
        """Bad JSON from LLM returns empty list — never crashes."""
        llm = self._make_llm("I cannot determine any tags for this note.")
        chain = LLMChain(llm=llm)
        results = await chain.run(
            context=make_context(),
            tags=[make_tag()],
            threshold=0.7,
        )
        assert results == []