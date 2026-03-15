"""
Langfuse observability — traces every LLM call.

Why observability:
  - See exactly what prompt was sent to the LLM
  - See exactly what the LLM returned
  - Track confidence scores over time
  - Debug why a tag was or wasn't applied
  - Monitor latency and token usage
"""
import logging
from functools import lru_cache

from tagging.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_langfuse_client():
    """
    Create Langfuse client once and cache it.
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
