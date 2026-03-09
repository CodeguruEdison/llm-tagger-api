import pytest

from unittest.mock import patch

from tagging.infrastructure.llm.factory import LLMFactory
from tagging.domain.enums.llm_provider import LLMProvider


class TestLLMFactory:
    def test_return_ollama_provider(self):
        """Factory returns Ollama chat model when provider is OLLAMA."""
        with patch("tagging.infrastructure.llm.factory.ChatOllama") as mock:
            factory =LLMFactory(
                provider = LLMProvider.OLLAMA,
                ollama_base_url="http://localhost:11434",
                ollama_model="llama3.2",
            )
            factory.create()
            mock.assert_called_once()
            
    def test_returns_openai_provider(self):
        """Factory returns OpenAI chat model when provider is OPENAI."""
        with patch("tagging.infrastructure.llm.factory.ChatOpenAI") as mock:
            factory = LLMFactory(
                provider=LLMProvider.OPENAI,
                openai_api_key="sk-test",
                openai_model="gpt-4o-mini",
            )
            factory.create()
            mock.assert_called_once()    
    def test_returns_azure_openai_provider(self):
        """Factory returns Azure OpenAI model when provider is AZURE_OPENAI."""
        with patch("tagging.infrastructure.llm.factory.AzureChatOpenAI") as mock:
            factory = LLMFactory(
                provider=LLMProvider.AZURE_OPENAI,
                azure_openai_endpoint="https://test.openai.azure.com",
                azure_openai_api_key="test-key",
                azure_openai_deployment="gpt-4o-mini",
                azure_openai_api_version="2024-02-01",
            )
            factory.create()
            mock.assert_called_once()

    def test_returns_anthropic_provider(self):
        """Factory returns Anthropic model when provider is ANTHROPIC."""
        with patch("tagging.infrastructure.llm.factory.ChatAnthropic") as mock:
            factory = LLMFactory(
                provider=LLMProvider.ANTHROPIC,
                anthropic_api_key="sk-ant-test",
                anthropic_model="claude-3-5-haiku-20241022",
            )
            factory.create()
            mock.assert_called_once()

    def test_invalid_provider_raises(self):
        """Unknown provider must fail immediately."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            factory = LLMFactory(provider="invalid")
            factory.create()