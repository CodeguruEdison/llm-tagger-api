"""
Langfuse observability — traces every LLM call.

Why observability:
  - See exactly what prompt was sent to the LLM
  - See exactly what the LLM returned
  - Track confidence scores over time
  - Debug why a tag was or wasn't applied
  - Monitor latency and token usage

Middleware: use get_langfuse_callback_handler() and pass it as config={"callbacks": [handler]}
to LangChain/LangGraph invokes so all LLM and pipeline runs are traced in one place.
"""
import logging
from functools import lru_cache
from typing import Any

from tagging.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_langfuse_client() -> Any | None:
    """
    Create Langfuse client once and cache it.
    Registers as the default client so CallbackHandler uses it.
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


@lru_cache
def get_langfuse_callback_handler() -> Any | None:
    """
    Return a LangChain/LangGraph CallbackHandler that sends all LLM and runnable
    traces to Langfuse. Use as middleware by passing to invokes:

        config = {}
        if handler := get_langfuse_callback_handler():
            config["callbacks"] = [handler]

        await llm.ainvoke(messages, config=config)
        # or
        await pipeline.ainvoke(state, config=config)

    Returns None if Langfuse is not configured. The handler uses the same client
    as get_langfuse_client() (created first so it becomes the default).
    """
    try:
        client = get_langfuse_client()
        if client is None:
            return None

        from langfuse.langchain import CallbackHandler

        # Uses get_client() under the hood, which returns our registered client
        handler = CallbackHandler(update_trace=True)
        return handler

    except Exception as e:
        logger.warning("Langfuse callback handler init failed: %s", str(e))
        return None
