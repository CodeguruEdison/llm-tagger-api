"""
Unit tests for LangGraph tagging pipeline.
TDD: RED before GREEN.

Tests cover:
  - Conditional edges (routing decisions)
  - Individual nodes (pure logic)
  - End-to-end pipeline invocation

No DB, no real LLM — pure logic testing.

Run: uv run pytest tests/unit/test_pipeline.py -v
"""

import pytest

from tagging.application.pipeline import (
    PIPELINE,
    PipelineState,
    merge_results_node,
    run_rules_node,
    should_run_llm,
    should_run_rules,
)
from tagging.domain.enums.condition_operator import ConditionOperator
from tagging.domain.enums.condition_type import ConditionType
from tagging.domain.enums.tag_source import TagSource
from tagging.domain.enums.tagging_mode import TaggingMode
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.domain.tag_result import TagResult
from tagging.domain.tag_rule import TagRule
from tagging.domain.tag_rule_condition import TagRuleCondition

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def make_tag(id="tag-1", slug="parts-delay") -> Tag:
    return Tag(
        id=id,
        category_id="cat-1",
        name="Parts Delay",
        slug=slug,
        description="Waiting on parts",
        color="#FF6B6B",
        icon="clock",
        priority=1,
        is_active=True,
    )


def make_context(text="waiting on parts") -> NoteContext:
    return NoteContext(
        note_id="note-1",
        ro_id="ro-1",
        shop_id="shop-1",
        text=text,
        event_type="note",
    )


def make_result(
    tag: Tag,
    confidence=1.0,
    source=TagSource.RULES,
) -> TagResult:
    return TagResult(
        tag=tag,
        confidence=confidence,
        source=source,
        reasoning="test",
    )


def base_state(**overrides) -> PipelineState:
    state = PipelineState(
        context=make_context(),
        tags=[make_tag()],
        rules=[],
        rules_results=[],
        llm_results=[],
        final_results=[],
        tagging_mode=TaggingMode.HYBRID,
        llm_confidence_threshold=0.7,
        llm_chain=None,
        error=None,
    )
    state.update(overrides)
    return state


# ─────────────────────────────────────────────
# Conditional Edge Tests
# ─────────────────────────────────────────────


class TestShouldRunRules:
    def test_llm_only_skips_rules(self):
        """LLM_ONLY routes directly to run_llm."""
        state = base_state(tagging_mode=TaggingMode.LLM_ONLY)
        assert should_run_rules(state) == "run_llm"

    def test_rules_only_runs_rules(self):
        """RULES_ONLY routes to run_rules."""
        state = base_state(tagging_mode=TaggingMode.RULES_ONLY)
        assert should_run_rules(state) == "run_rules"

    def test_hybrid_runs_rules(self):
        """HYBRID routes to run_rules first."""
        state = base_state(tagging_mode=TaggingMode.HYBRID)
        assert should_run_rules(state) == "run_rules"


class TestShouldRunLLM:
    def test_rules_only_skips_llm(self):
        """RULES_ONLY routes directly to merge."""
        state = base_state(tagging_mode=TaggingMode.RULES_ONLY)
        assert should_run_llm(state) == "merge"

    def test_hybrid_runs_llm(self):
        """HYBRID routes to run_llm after rules."""
        state = base_state(tagging_mode=TaggingMode.HYBRID)
        assert should_run_llm(state) == "run_llm"

    def test_llm_only_runs_llm(self):
        """LLM_ONLY routes to run_llm."""
        state = base_state(tagging_mode=TaggingMode.LLM_ONLY)
        assert should_run_llm(state) == "run_llm"


# ─────────────────────────────────────────────
# Node Tests
# ─────────────────────────────────────────────


class TestRunRulesNode:
    def test_returns_matching_rules(self):
        """Rules engine evaluates and returns matches."""
        tag = make_tag()
        rule = TagRule(
            id="rule-1",
            tag_id="tag-1",
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
        state = base_state(tags=[tag], rules=[rule])
        result = run_rules_node(state)
        assert len(result["rules_results"]) == 1
        assert result["rules_results"][0].tag.slug == "parts-delay"

    def test_returns_empty_when_no_matches(self):
        """Returns empty list when no rules match."""
        tag = make_tag()
        rule = TagRule(
            id="rule-1",
            tag_id="tag-1",
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
        state = base_state(
            context=make_context("vehicle is ready for pickup"),
            tags=[tag],
            rules=[rule],
        )
        result = run_rules_node(state)
        assert result["rules_results"] == []


class TestMergeResultsNode:
    def test_rules_only_result(self):
        """Returns rules results when no LLM results."""
        tag = make_tag()
        rules_result = make_result(tag)
        state = base_state(rules_results=[rules_result])
        result = merge_results_node(state)
        assert len(result["final_results"]) == 1
        assert result["final_results"][0].source == TagSource.RULES

    def test_rules_win_on_conflict(self):
        """Rules result wins when both match same tag."""
        tag = make_tag()
        rules_result = make_result(tag, confidence=1.0, source=TagSource.RULES)
        llm_result = make_result(tag, confidence=0.9, source=TagSource.LLM)
        state = base_state(
            rules_results=[rules_result],
            llm_results=[llm_result],
        )
        result = merge_results_node(state)
        assert len(result["final_results"]) == 1
        assert result["final_results"][0].source == TagSource.RULES

    def test_llm_tag_added_when_above_threshold(self):
        """LLM tag added if not covered by rules and above threshold."""
        rules_tag = make_tag(id="tag-1", slug="parts-delay")
        llm_tag = make_tag(id="tag-2", slug="customer-concern")
        rules_result = make_result(rules_tag)
        llm_result = make_result(llm_tag, confidence=0.9, source=TagSource.LLM)
        state = base_state(
            rules_results=[rules_result],
            llm_results=[llm_result],
        )
        result = merge_results_node(state)
        assert len(result["final_results"]) == 2

    def test_llm_tag_ignored_below_threshold(self):
        """LLM result below confidence threshold is ignored."""
        tag = make_tag()
        llm_result = make_result(tag, confidence=0.5, source=TagSource.LLM)
        state = base_state(llm_results=[llm_result])
        result = merge_results_node(state)
        assert len(result["final_results"]) == 0

    def test_sorted_by_confidence_descending(self):
        """Final results sorted by confidence descending."""
        tag1 = make_tag(id="tag-1", slug="parts-delay")
        tag2 = make_tag(id="tag-2", slug="customer-concern")
        result1 = make_result(tag1, confidence=0.8, source=TagSource.RULES)
        result2 = make_result(tag2, confidence=1.0, source=TagSource.RULES)
        state = base_state(rules_results=[result1, result2])
        result = merge_results_node(state)
        assert result["final_results"][0].confidence == 1.0
        assert result["final_results"][1].confidence == 0.8


# ─────────────────────────────────────────────
# End-to-End Tests
# ─────────────────────────────────────────────


class TestPipelineEndToEnd:
    @pytest.mark.asyncio
    async def test_rules_only_pipeline(self):
        """Full pipeline in RULES_ONLY mode — tag applied."""
        tag = make_tag()
        rule = TagRule(
            id="rule-1",
            tag_id="tag-1",
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
        state = base_state(
            context=make_context("waiting on parts from LKQ"),
            tags=[tag],
            rules=[rule],
            tagging_mode=TaggingMode.RULES_ONLY,
        )
        result = await PIPELINE.ainvoke(state)
        assert len(result["final_results"]) == 1
        assert result["final_results"][0].tag.slug == "parts-delay"
        assert result["final_results"][0].source == TagSource.RULES

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self):
        """Pipeline returns empty when no rules match."""
        tag = make_tag()
        rule = TagRule(
            id="rule-1",
            tag_id="tag-1",
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
        state = base_state(
            context=make_context("vehicle is ready for pickup"),
            tags=[tag],
            rules=[rule],
            tagging_mode=TaggingMode.RULES_ONLY,
        )
        result = await PIPELINE.ainvoke(state)
        assert len(result["final_results"]) == 0

    @pytest.mark.asyncio
    async def test_llm_only_with_no_chain_returns_empty(self):
        """LLM_ONLY with no chain injected returns empty gracefully."""
        state = base_state(
            tagging_mode=TaggingMode.LLM_ONLY,
            llm_chain=None,
        )
        result = await PIPELINE.ainvoke(state)
        assert len(result["final_results"]) == 0
        assert result["error"] is None
