"""
Orchestrator — entry point to the tagging pipeline.


Responsibilities:
  1. Load taxonomy from DB (tags + rules)
  2. Build LLMChain if needed
  3. Invoke LangGraph pipeline
  4. Save results to DB
  5. Return final list[TagResult]

This is the only place that knows about all the pieces.
Everything else is injected — easy to test, easy to swap.

Langfuse: pass langfuse_handler so the full pipeline run is traced as one trace
in Langfuse (with nested LLM spans from the chain).
"""
import asyncio
import logging
from typing import Any

from tagging.application.interfaces import ITagRepository
from tagging.application.pipeline import PIPELINE, PipelineState
from tagging.domain.enums.tagging_mode import TaggingMode
from tagging.domain.note_context import NoteContext
from tagging.domain.tag_result import TagResult

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Coordinates the full tagging flow for a single note.

    Usage:
        orchestrator = Orchestrator(
            repository=repo,
            tagging_mode=TaggingMode.HYBRID,
            llm_confidence_threshold=0.7,
            llm_chain=chain,   # optional, None for RULES_ONLY
            langfuse_handler=handler,  # optional, traces pipeline + LLM in Langfuse
        )
        results = await orchestrator.tag_note(context)
    """

    def __init__(
        self,
        repository: ITagRepository,
        tagging_mode: TaggingMode = TaggingMode.HYBRID,
        llm_confidence_threshold: float = 0.7,
        llm_chain: object | None = None,
        langfuse_client: Any | None = None,
    ) -> None:
        self._repository = repository
        self._tagging_mode = tagging_mode
        self._llm_confidence_threshold = llm_confidence_threshold
        self._llm_chain = llm_chain
        self._langfuse_client = langfuse_client

    async def tag_note(
        self, context: NoteContext
    ) -> list[TagResult]:
        """
        Run the full tagging pipeline for a single note.

        Steps:
          1. Load taxonomy from DB
          2. Build pipeline state
          3. Invoke LangGraph pipeline
          4. Save each result to DB
          5. Return final results

        Never raises — errors are logged and empty list returned.
        """
        try:
            # Load taxonomy
            tags = await self._repository.get_all_active_tags()
            rules = await self._repository.get_all_active_rules()

            # Build initial state
            state = PipelineState(
                context=context,
                tags=tags,
                rules=rules,
                rules_results=[],
                llm_results=[],
                final_results=[],
                tagging_mode=self._tagging_mode,
                llm_confidence_threshold=self._llm_confidence_threshold,
                llm_chain=self._llm_chain,
                error=None,
            )

            result_state = await PIPELINE.ainvoke(state)

            # Flush Langfuse so traces appear immediately in the dashboard
            from tagging.infrastructure.observability import flush_langfuse
            await asyncio.to_thread(flush_langfuse, self._langfuse_client)

            # Log any LLM errors — pipeline still returns rules results
            if result_state.get("error"):
                logger.warning(
                    "Pipeline error for note %s: %s",
                    context.note_id,
                    result_state["error"],
                )

            final_results = result_state.get("final_results", [])

            # Persist each result
            for result in final_results:
                await self._repository.save_tag_result(context, result)

            return final_results

        except Exception as e:
            logger.error(
                "Orchestrator failed for note %s: %s",
                context.note_id,
                str(e),
            )
            return []
