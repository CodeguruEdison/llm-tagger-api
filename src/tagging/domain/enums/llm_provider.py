"""LLMProvider enum — supported LLM providers."""
from enum import Enum


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"