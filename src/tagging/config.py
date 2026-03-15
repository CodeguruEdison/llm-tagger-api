"""
Application configuration using pydantic-settings.

Reads from environment variables automatically.
Validates all values at startup — fail fast, fail clear.

Usage:
    from tagging.config import get_settings
    settings = get_settings()
    print(settings.llm_provider)
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tagging.domain.enums import LLMProvider, TaggingMode


class Settings(BaseSettings):
    """
    All application settings in one place.

    pydantic-settings reads these from environment variables.
    Variable names are UPPERCASE in env, lowercase in code.

    Example:
        LLM_PROVIDER=ollama  →  settings.llm_provider == LLMProvider.OLLAMA
        TAGGING_MODE=hybrid  →  settings.tagging_mode == TaggingMode.HYBRID
    """

    model_config = SettingsConfigDict(
        env_file=".env",  # load from .env file if present
        env_file_encoding="utf-8",
        case_sensitive=False,  # LLM_PROVIDER == llm_provider
        extra="ignore",  # ignore unknown env vars
    )

    # ── Database ──────────────────────────────────────────
    database_url: str
    direct_database_url: str | None = (
        None  # use when pgBouncer causes auth issues (e.g. Docker)
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ─────────────────────────────────────────────
    redis_url: str
    arq_redis_url: str
    redis_taxonomy_ttl: int = 300  # 5 minutes

    # ── Tagging Pipeline ──────────────────────────────────
    tagging_mode: TaggingMode = TaggingMode.HYBRID
    llm_confidence_threshold: float = 0.7  # ignore LLM results below this
    rules_confidence: float = 1.0  # rules are always deterministic

    # ── LLM Provider ──────────────────────────────────────
    llm_provider: LLMProvider

    # ── Ollama ────────────────────────────────────────────
    ollama_base_url: str | None = None
    ollama_model: str | None = "gemma2:9b"

    # ── OpenAI ────────────────────────────────────────────
    openai_api_key: str | None = None
    openai_model: str | None = "gpt-4o-mini"

    # ── Azure OpenAI ──────────────────────────────────────
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str | None = "2024-02-01"

    # ── Anthropic ─────────────────────────────────────────
    anthropic_api_key: str | None = None
    anthropic_model: str | None = "claude-3-5-haiku-20241022"

    # ── Langfuse ──────────────────────────────────────────
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = "http://localhost:3001"

    # ── Worker ────────────────────────────────────────────
    worker_max_jobs: int = 10
    worker_job_timeout: int = 60
    worker_max_tries: int = 3

    # ── API ───────────────────────────────────────────────
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    @model_validator(mode="after")
    def validate_provider_settings(self) -> "Settings":
        """
        Cross-field validation.
        Each provider requires its own set of settings.
        Fail at startup with a clear message — not at
        runtime when the first note comes in.

        This is enterprise-grade configuration validation:
        the app either starts correctly or not at all.
        """
        if self.llm_provider == LLMProvider.OLLAMA:
            if not self.ollama_base_url:
                raise ValueError(
                    "OLLAMA_BASE_URL is required when LLM_PROVIDER=ollama. "
                    "Install Ollama from https://ollama.ai and set "
                    "OLLAMA_BASE_URL=http://localhost:11434"
                )

        elif self.llm_provider == LLMProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")

        elif self.llm_provider == LLMProvider.AZURE_OPENAI:
            if not self.azure_openai_endpoint or not self.azure_openai_api_key:
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are "
                    "required when LLM_PROVIDER=azure_openai."
                )

        elif self.llm_provider == LLMProvider.ANTHROPIC:
            if not self.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    """
    Returns cached Settings instance.

    lru_cache means Settings is created ONCE and reused.
    Why: reading env vars and validating on every request
    would be wasteful. Cache it at startup, reuse forever.

    In tests, call get_settings.cache_clear() to reset.
    """
    return Settings()
