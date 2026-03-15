"""
LLM Chain — wraps the LLM call with prompt, parsing, and validation.

Responsibilities:
  1. Format prompt with taxonomy + note text
  2. Call LLM asynchronously
  3. Parse JSON response
  4. Match slugs back to Tag domain objects
  5. Filter by confidence threshold
  6. Never crash — return empty list on any failure
"""
import json
import logging
from typing import Any, cast

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
          3. Call LLM
          4. Parse JSON
          5. Match slugs → Tag objects
          6. Filter by threshold

        Returns empty list on any failure — never raises.
        """
        if not tags:
            return []
        # Start Langfuse trace
        from tagging.infrastructure.observability import get_langfuse_client
        langfuse = get_langfuse_client()
        trace = None
        generation = None

        if langfuse:
            trace = cast(Any, langfuse).trace(
                name="tag_note",
                input={"note_id": context.note_id, "text": context.text},
                metadata={"shop_id": context.shop_id, "ro_id": context.ro_id},
            )


        try:
            # Build slug → Tag lookup for O(1) matching
            tag_by_slug = {tag.slug: tag for tag in tags}

            # Format prompt
            taxonomy = build_taxonomy_context(tags)
            messages = TAGGING_PROMPT.format_messages(
                taxonomy=taxonomy,
                note_text=context.text,
            )
            # Log generation start
            if trace:
                generation = trace.generation(
                    name="llm_tagging",
                    input=messages[1].content,
                    model=getattr(self._llm, "model", "unknown"),
                )
                # Call LLM
            response = await self._llm.ainvoke(messages)
            # Log generation end
            if generation:
                generation.end(output=response.content)

            # Parse JSON (content may be str or list for multimodal)
            content = response.content
            if not isinstance(content, str):
                logger.warning("LLM returned non-string content, skipping")
                return []
            raw = self._parse_json(content)
            if raw is None:
                return []

            # Build TagResults
            results = []
            for item in raw:
                result = self._build_result(item, tag_by_slug, threshold)
                if result:
                    results.append(result)
            # Log final results to trace
            if trace:
                trace.update(
                    output={
                        "tags": [r.tag.slug for r in results],
                        "total": len(results),
                    }
                )
            if langfuse:
                cast(Any, langfuse).flush()

            return results

        except Exception as e:
            if trace:
                trace.update(
                    output={"error": str(e)},
                    level="ERROR",
                )
            if langfuse:
                cast(Any, langfuse).flush()
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
            # Strip markdown code fences if present
            clean = content.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                # Remove first line (```json or ```) and last line (```)
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

            # Ignore unknown slugs — LLM hallucinated a tag
            tag = tag_by_slug.get(slug)
            if not tag:
                logger.debug("LLM returned unknown slug: %s", slug)
                return None

            # Ignore low confidence results
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

