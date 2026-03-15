"""Unit tests for Langfuse observability."""
from unittest.mock import MagicMock, patch

from tagging.infrastructure.observability import flush_langfuse


class TestFlushLangfuse:

    def test_noop_when_client_is_none(self):
        flush_langfuse(None)  # must not raise

    def test_flushes_langfuse_client(self):
        mock_client = MagicMock()
        mock_client.tracing_enabled = True
        flush_langfuse(mock_client)
        mock_client.flush.assert_called_once()

    def test_does_not_flush_when_tracing_disabled(self):
        mock_client = MagicMock()
        mock_client.tracing_enabled = False
        flush_langfuse(mock_client)
        mock_client.flush.assert_not_called()


class TestGetLangfuseClient:

    def test_returns_none_when_not_configured(self, monkeypatch):
        from tagging.infrastructure.observability import get_langfuse_client
        get_langfuse_client.cache_clear()
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
        from tagging.config import get_settings
        get_settings.cache_clear()
        assert get_langfuse_client() is None
        get_langfuse_client.cache_clear()
        get_settings.cache_clear()

    def test_returns_client_when_configured(self, monkeypatch):
        from tagging.infrastructure.observability import get_langfuse_client
        get_langfuse_client.cache_clear()
        with patch("langfuse.Langfuse") as mock_langfuse:
            mock_langfuse.return_value = MagicMock()
            monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
            monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
            monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")
            from tagging.config import get_settings
            get_settings.cache_clear()
            assert get_langfuse_client() is not None
            get_langfuse_client.cache_clear()
            get_settings.cache_clear()


class TestCreateLangfuseCallbackHandler:

    def test_returns_none_tuple_when_not_configured(self, monkeypatch):
        from tagging.infrastructure.observability import (
            create_langfuse_callback_handler,
            get_langfuse_client,
        )
        get_langfuse_client.cache_clear()
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
        from tagging.config import get_settings
        get_settings.cache_clear()
        trace, handler = create_langfuse_callback_handler(note_id="note-1")
        assert trace is None
        assert handler is None
        get_langfuse_client.cache_clear()
        get_settings.cache_clear()

    def test_returns_trace_and_handler_when_configured(self, monkeypatch):
        from tagging.infrastructure.observability import (
            create_langfuse_callback_handler,
            get_langfuse_client,
        )
        get_langfuse_client.cache_clear()
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
        monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")
        from tagging.config import get_settings
        get_settings.cache_clear()

        mock_span = MagicMock()
        mock_span.trace_id = "trace-abc"
        mock_client = MagicMock()
        mock_client.start_observation.return_value = mock_span
        mock_handler = MagicMock()

        with patch("langfuse.Langfuse", return_value=mock_client), \
             patch("langfuse.langchain.CallbackHandler", return_value=mock_handler) as MockHandler:
            trace, handler = create_langfuse_callback_handler(
                note_id="note-42",
                shop_id="shop-1",
            )
            assert trace is mock_span
            assert handler is mock_handler
            # trace_context carries the trace_id for span nesting
            _, kwargs = MockHandler.call_args
            assert kwargs["trace_context"]["trace_id"] == "trace-abc"

        get_langfuse_client.cache_clear()
        get_settings.cache_clear()
