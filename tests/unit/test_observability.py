"""Unit tests for Langfuse observability."""
from unittest.mock import MagicMock, patch


class TestGetLangfuseClient:

    def test_returns_none_when_not_configured(self, monkeypatch):
        """Returns None when Langfuse keys not set."""
        from tagging.infrastructure.observability import get_langfuse_client
        get_langfuse_client.cache_clear()

        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")

        from tagging.config import get_settings
        get_settings.cache_clear()

        client = get_langfuse_client()
        assert client is None

        get_langfuse_client.cache_clear()
        get_settings.cache_clear()

    def test_returns_client_when_configured(self, monkeypatch):
        """Returns Langfuse client when keys are set."""
        from tagging.infrastructure.observability import get_langfuse_client
        get_langfuse_client.cache_clear()

        with patch("langfuse.Langfuse") as mock_langfuse:
            mock_client = MagicMock()
            mock_langfuse.return_value = mock_client

            monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
            monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
            monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")

            from tagging.config import get_settings
            get_settings.cache_clear()

            client = get_langfuse_client()
            assert client is not None

            get_langfuse_client.cache_clear()
            get_settings.cache_clear()
