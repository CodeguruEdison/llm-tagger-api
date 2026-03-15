"""LLMProvider enum — supported LLM providers."""

from enum import StrEnum


class LLMProvider(StrEnum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
