"""
Langfuse observability — traces every LLM call.

Why observability:
  - See exactly what prompt was sent to the LLM
  - See exactly what the LLM returned
  - Track confidence scores over time
  - Debug why a tag was or wasn't applied
  - Monitor latency and token usage

Usage:
  1. Call create_langfuse_callback_handler(session_id, metadata) per request and
     pass the returned handler as config={"callbacks": [handler]} to LangChain
     invokes. Each request gets its own handler so traces carry per-request context
     (note_id, shop_id).
  2. Call flush_langfuse() after each request — it flushes the global Langfuse
     client which shares the OTEL batch exporter used by all handlers.

Note: requires Langfuse SDK v3 + Langfuse server v3.
"""
import logging
from functools import lru_cache
from typing import Any

from tagging.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_langfuse_client() -> Any | None:
    """
    Cached Langfuse client — used only for flush().
    Returns None if Langfuse is not configured.
    """
    try:
        from langfuse import Langfuse

        settings = get_settings()
        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            logger.info("Langfuse not configured — observability disabled")
            return None

        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info("Langfuse connected at %s", settings.langfuse_host)
        return client

    except Exception as e:
        logger.warning("Langfuse init failed: %s", str(e))
        return None


def create_langfuse_callback_handler(
    note_id: str | None = None,
    shop_id: str | None = None,
    ro_id: str | None = None,
) -> tuple[Any, Any] | tuple[None, None]:
    """
    Create a parent trace + a LangChain CallbackHandler for a single request.

    Returns (trace_span, handler) so the caller can:
      - Pass handler as config={"callbacks": [handler]} to llm.ainvoke()
      - Call trace_span.end(output=...) after the LLM call to close the trace

    LangChain spans are automatically nested inside the trace, giving full
    per-request context (note_id, shop_id) in the Langfuse UI.

    Returns (None, None) if Langfuse is not configured.
    """
    try:
        client = get_langfuse_client()
        if client is None:
            return None, None

        from langfuse.langchain import CallbackHandler
        from langfuse.types import TraceContext

        # Create the parent trace with per-request metadata
        trace = client.start_observation(
            name="tag_note",
            as_type="span",
            input={"note_id": note_id},
            metadata={"shop_id": shop_id, "ro_id": ro_id},
        )

        # Link the callback handler to this trace so LangChain spans are children
        handler = CallbackHandler(
            trace_context=TraceContext(trace_id=trace.trace_id),
        )
        return trace, handler

    except Exception as e:
        logger.warning("Langfuse callback handler init failed: %s", str(e))
        return None, None


def flush_langfuse(client: Any | None = None) -> None:
    """
    Flush pending Langfuse traces so they appear immediately in the dashboard.
    Call this after each request. Pass the cached client from get_langfuse_client().
    """
    try:
        if client is not None and getattr(client, "tracing_enabled", True):
            client.flush()
    except Exception as e:
        logger.debug("Langfuse flush failed: %s", e)
