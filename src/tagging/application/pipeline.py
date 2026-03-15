"""
LangGraph tagging pipeline.

Graph structure:
  START
    ↓
  should_run_rules?    ← conditional edge based on TaggingMode
    ↙           ↘
  run_rules     (skip to run_llm)
    ↓
  should_run_llm?      ← conditional edge based on TaggingMode
    ↙           ↘
  run_llm       (skip to merge)
    ↘           ↙
  merge_results        ← combine + deduplicate
    ↓
  END

Rules:
  RULES_ONLY → run_rules → merge         (LLM skipped)
  LLM_ONLY   → run_llm → merge           (rules skipped)
  HYBRID     → run_rules → run_llm → merge

Nodes = pure logic, no routing decisions.
Edges = all routing decisions live here.
State = data flowing through every node.
"""
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from tagging.application.rules_engine import RulesEngine
from tagging.domain.enums.tagging_mode import TaggingMode
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.domain.tag_result import TagResult
from tagging.domain.tag_rule import TagRule

# ─────────────────────────────────────────────
# Pipeline State
# ─────────────────────────────────────────────

class PipelineState(TypedDict):
    """
    State passed between all nodes in the graph.

    Every node reads what it needs and writes its output back.
    LangGraph merges the returned dict into the current state.
    """
    context: NoteContext
    tags: list[Tag]
    rules: list[TagRule]
    rules_results: list[TagResult]
    llm_results: list[TagResult]
    final_results: list[TagResult]
    tagging_mode: TaggingMode
    llm_confidence_threshold: float
    llm_chain: Any | None        # injected by orchestrator, None in RULES_ONLY
    error: str | None


# ─────────────────────────────────────────────
# Nodes — pure logic, no routing
# ─────────────────────────────────────────────

def run_rules_node(state: PipelineState) -> dict:
    """
    Fast path: evaluate all rules against the note.

    Pure Python logic — no I/O, no routing decisions.
    Target: < 1ms per note.
    Routing (whether to call this node) is handled by should_run_rules edge.
    """
    engine = RulesEngine()
    results = engine.evaluate(
        context=state["context"],
        tags=state["tags"],
        rules=state["rules"],
    )
    return {"rules_results": results}


async def run_llm_node(state: PipelineState) -> dict:
    """
    Smart path: ask LLM to tag the note.

    llm_chain is injected via state:
      - Production: real LLM chain from LLMFactory
      - Tests: mock that returns controlled results
      - None: graceful skip with empty results

    LLM failure must never crash the pipeline.
    Rules results are still valid and returned even if LLM fails.
    """
    llm_chain = state.get("llm_chain")
    if not llm_chain:
        return {"llm_results": []}

    try:
        results = await llm_chain.run(
            context=state["context"],
            tags=state["tags"],
            threshold=state["llm_confidence_threshold"],
        )
        return {"llm_results": results}
    except Exception as e:
        return {
            "llm_results": [],
            "error": f"LLM failed: {str(e)}",
        }


def merge_results_node(state: PipelineState) -> dict:
    """
    Merge rules + LLM results and deduplicate.

    Deduplication rules:
      1. Same tag from both sources → rules result wins
         (rules are deterministic, LLM is probabilistic)
      2. LLM-only tags added if confidence >= threshold
      3. Rules-only tags always included (confidence=1.0)

    Final results sorted by confidence descending.
    """
    rules_results = state.get("rules_results", [])
    llm_results = state.get("llm_results", [])
    threshold = state.get("llm_confidence_threshold", 0.7)

    # Track tag_ids already covered by rules
    rules_tag_ids = {r.tag.id for r in rules_results}

    # Start with all rules results
    merged = list(rules_results)

    # Add LLM results only if:
    # 1. Tag not already covered by rules
    # 2. Confidence meets threshold
    for llm_result in llm_results:
        if (
            llm_result.tag.id not in rules_tag_ids
            and llm_result.confidence >= threshold
        ):
            merged.append(llm_result)

    # Sort by confidence descending
    merged.sort(key=lambda r: r.confidence, reverse=True)

    return {"final_results": merged}


# ─────────────────────────────────────────────
# Conditional Edges — all routing decisions
# ─────────────────────────────────────────────

def should_run_rules(state: PipelineState) -> str:
    """
    Decides whether to run the rules engine.

    LLM_ONLY → skip rules, go straight to LLM
    RULES_ONLY / HYBRID → run rules first
    """
    if state["tagging_mode"] == TaggingMode.LLM_ONLY:
        return "run_llm"
    return "run_rules"


def should_run_llm(state: PipelineState) -> str:
    """
    Decides whether to run the LLM after rules.

    RULES_ONLY → skip LLM, go straight to merge
    HYBRID     → run LLM after rules
    """
    if state["tagging_mode"] == TaggingMode.RULES_ONLY:
        return "merge"
    return "run_llm"


# ─────────────────────────────────────────────
# Graph Assembly
# ─────────────────────────────────────────────

def build_pipeline() -> Any:
    """
    Assemble and compile the LangGraph pipeline.

    Called once at startup — returns compiled graph.
    Compiled graph is thread-safe and reusable.
    """
    graph = StateGraph(PipelineState)

    # ── Nodes ──────────────────────────────────
    graph.add_node("run_rules", run_rules_node)
    graph.add_node("run_llm", run_llm_node)
    graph.add_node("merge", merge_results_node)

    # ── Edges ──────────────────────────────────

    # Entry: decide whether to run rules or skip to LLM
    graph.add_conditional_edges(
        START,
        should_run_rules,
        {
            "run_rules": "run_rules",
            "run_llm": "run_llm",
        },
    )

    # After rules: decide whether to run LLM or skip to merge
    graph.add_conditional_edges(
        "run_rules",
        should_run_llm,
        {
            "run_llm": "run_llm",
            "merge": "merge",
        },
    )

    # LLM always leads to merge
    graph.add_edge("run_llm", "merge")

    # Merge leads to end
    graph.add_edge("merge", END)

    return graph.compile()


# ─────────────────────────────────────────────
# Compiled Pipeline
# ─────────────────────────────────────────────

# Built once at module load — reused for every note
PIPELINE = build_pipeline()
