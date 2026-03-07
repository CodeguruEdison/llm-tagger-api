"""
Unit tests for application configuration.
TDD: RED before GREEN.

Run: uv run pytest tests/unit/test_config.py -v --no-cov
Expected: RED (ModuleNotFoundError)
"""
import pytest
from pydantic import ValidationError

from tagging.config import Settings
from tagging.domain.enums import LLMProvider, TaggingMode


class TestSettings:

    def test_default_tagging_mode_is_hybrid(self):
        """
        Hybrid must be the default.
        Best accuracy out of the box.
        Operators can downgrade if needed.
        """
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            redis_url="redis://localhost:6379/0",
            arq_redis_url="redis://localhost:6379/1",
            llm_provider=LLMProvider.OLLAMA,
            ollama_base_url="http://localhost:11434",
            ollama_model="gemma2:9b",
        )
        assert settings.tagging_mode == TaggingMode.HYBRID

    def test_can_set_rules_only_mode(self):
        """Rules only mode disables LLM completely."""
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            redis_url="redis://localhost:6379/0",
            arq_redis_url="redis://localhost:6379/1",
            llm_provider=LLMProvider.OLLAMA,
            ollama_base_url="http://localhost:11434",
            ollama_model="gemma2:9b",
            tagging_mode=TaggingMode.RULES_ONLY,
        )
        assert settings.tagging_mode == TaggingMode.RULES_ONLY

    def test_database_url_required(self):
        """Missing database URL must fail at startup."""
        with pytest.raises(ValidationError):
            Settings(
                redis_url="redis://localhost:6379/0",
                arq_redis_url="redis://localhost:6379/1",
                llm_provider=LLMProvider.OLLAMA,
                ollama_base_url="http://localhost:11434",
                ollama_model="gemma2:9b",
            )

    def test_ollama_requires_base_url(self):
        """
        When provider is Ollama, base URL is required.
        Without it we cannot connect to Ollama.
        Fail at startup — not on first tagging request.
        """
        with pytest.raises(ValidationError):
            Settings(
                database_url="postgresql+asyncpg://user:pass@localhost/db",
                redis_url="redis://localhost:6379/0",
                arq_redis_url="redis://localhost:6379/1",
                llm_provider=LLMProvider.OLLAMA,
                ollama_base_url=None,   # missing — must fail
                ollama_model="gemma2:9b",
            )

    def test_openai_requires_api_key(self):
        """When provider is OpenAI, API key is required."""
        with pytest.raises(ValidationError):
            Settings(
                database_url="postgresql+asyncpg://user:pass@localhost/db",
                redis_url="redis://localhost:6379/0",
                arq_redis_url="redis://localhost:6379/1",
                llm_provider=LLMProvider.OPENAI,
                openai_api_key=None,    # missing — must fail
            )

    def test_azure_requires_endpoint_and_key(self):
        """Azure OpenAI needs both endpoint and API key."""
        with pytest.raises(ValidationError):
            Settings(
                database_url="postgresql+asyncpg://user:pass@localhost/db",
                redis_url="redis://localhost:6379/0",
                arq_redis_url="redis://localhost:6379/1",
                llm_provider=LLMProvider.AZURE_OPENAI,
                azure_openai_endpoint=None,   # missing — must fail
                azure_openai_api_key=None,
            )

    def test_invalid_tagging_mode_fails(self):
        """Invalid mode must fail immediately."""
        with pytest.raises(ValidationError):
            Settings(
                database_url="postgresql+asyncpg://user:pass@localhost/db",
                redis_url="redis://localhost:6379/0",
                arq_redis_url="redis://localhost:6379/1",
                llm_provider=LLMProvider.OLLAMA,
                ollama_base_url="http://localhost:11434",
                ollama_model="gemma2:9b",
                tagging_mode="invalid_mode",  # must fail
            )

    def test_reads_from_environment_variables(self, monkeypatch):
        """
        Settings must read from environment variables.
        This is the core feature of pydantic-settings.
        How Docker and production deployments configure the app.
        """
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("ARQ_REDIS_URL", "redis://localhost:6379/1")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "gemma2:9b")
        monkeypatch.setenv("TAGGING_MODE", "rules_only")

        settings = Settings()
        assert settings.llm_provider == LLMProvider.OLLAMA
        assert settings.tagging_mode == TaggingMode.RULES_ONLY