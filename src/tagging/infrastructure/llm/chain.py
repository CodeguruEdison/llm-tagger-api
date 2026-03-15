"""
LLM Chain — wraps the LLM call with prompt, parsing, and validation.

Responsibilities:
  1. Format prompt with taxonomy + note text
  2. Call LLM asynchronously
  3. Parse JSON response
  4. Match slugs back to Tag domain objects
  5. Filter by confidence threshold
  6. Never crash — return empty list on any failure

Langfuse: a per-request CallbackHandler is created inside run() so each LLM
call is automatically traced as a Langfuse session keyed to the note_id.
No manual trace/generation code needed — the v3 SDK handles it via OTEL.
"""

import json
import logging

from langchain_core.language_models import BaseChatModel

from tagging.domain.enums.tag_source import TagSource
from tagging.domain.note_context import NoteContext
from tagging.domain.tag import Tag
from tagging.domain.tag_result import TagResult
from tagging.infrastructure.llm.prompts import TAGGING_PROMPT, build_taxonomy_context

logger = logging.getLogger(__name__)


class LLMChain:
    """
    Wraps a LangChain LLM with our tagging prompt and output parsing.

    Usage:
        chain = LLMChain(llm=factory.create())
        results = await chain.run(context, tags, threshold=0.7)
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def run(
        self,
        context: NoteContext,
        tags: list[Tag],
        threshold: float = 0.7,
    ) -> list[TagResult]:
        """
        Run the LLM tagging chain.

        Steps:
          1. Build taxonomy string from tags
          2. Format prompt
          3. Call LLM (with per-request Langfuse callback if configured)
          4. Parse JSON
          5. Match slugs → Tag objects
          6. Filter by threshold

        Returns empty list on any failure — never raises.
        """
        if not tags:
            return []

        # Per-request Langfuse trace + callback — LangChain spans are nested
        # inside the trace so each request appears as one trace in the UI.
        trace, handler = None, None
        try:
            from tagging.infrastructure.observability import (
                create_langfuse_callback_handler,
            )

            trace, handler = create_langfuse_callback_handler(
                note_id=context.note_id,
                shop_id=context.shop_id,
                ro_id=context.ro_id,
            )
        except Exception as e:
            logger.debug("Langfuse handler setup failed: %s", e)

        run_config = {"callbacks": [handler]} if handler else {}

        try:
            tag_by_slug = {tag.slug: tag for tag in tags}

            taxonomy = build_taxonomy_context(tags)
            messages = TAGGING_PROMPT.format_messages(
                taxonomy=taxonomy,
                note_text=context.text,
            )

            response = await self._llm.ainvoke(messages, config=run_config)

            content = response.content
            if not isinstance(content, str):
                logger.warning("LLM returned non-string content, skipping")
                return []

            raw = self._parse_json(content)
            if raw is None:
                return []

            results = []
            for item in raw:
                result = self._build_result(item, tag_by_slug, threshold)
                if result:
                    results.append(result)

            if trace:
                try:
                    trace.end(output={"tags": [r.tag.slug for r in results]})
                except Exception:
                    pass

            return results

        except Exception as e:
            if trace:
                try:
                    trace.end(output={"error": str(e)}, level="ERROR")
                except Exception:
                    pass
            logger.warning("LLM chain failed: %s", str(e))
            return []

    def _parse_json(self, content: str) -> list | None:
        """
                Parse JSON from LLM response.

                LLMs sometimes wrap JSON in markdown code blocks:
        ```json\n[...]\n```
                We strip those before parsing.

                Returns None if parsing fails.
        """
        try:
            clean = content.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1])
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            logger.warning("LLM returned invalid JSON: %s", content[:200])
            return None

    def _build_result(
        self,
        item: dict,
        tag_by_slug: dict[str, Tag],
        threshold: float,
    ) -> TagResult | None:
        """
        Build a TagResult from a single LLM output item.

        Returns None if:
          - slug not found in taxonomy (hallucination)
          - confidence below threshold
          - missing required fields
        """
        try:
            if not isinstance(item, dict):
                logger.debug("LLM returned non-dict item: %r", item)
                return None

            slug = item.get("tag_slug", "")
            confidence = float(item.get("confidence", 0.0))
            reasoning = item.get("reasoning", "")

            tag = tag_by_slug.get(slug)
            if not tag:
                logger.debug("LLM returned unknown slug: %s", slug)
                return None

            if confidence < threshold:
                return None

            return TagResult(
                tag=tag,
                confidence=confidence,
                source=TagSource.LLM,
                reasoning=reasoning or f"LLM matched tag: {slug}",
            )

        except Exception as e:
            logger.warning("Failed to build TagResult: %s", str(e))
            return None
