"""
LLM Provider Factory.

Returns the correct LangChain chat model based on LLM_PROVIDER.
Zero code changes needed to switch providers — just change env var.

Usage:
    factory = LLMFactory(provider=LLMProvider.OLLAMA, ...)
    llm = factory.create()  # returns BaseChatModel
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel

from langchain_ollama import ChatOllama

from langchain_openai import AzureChatOpenAI,ChatOpenAI

from langchain_anthropic import ChatAnthropic

from tagging.domain.enums.llm_provider import LLMProvider

class LLMFactory:
    """
    Creates the correct LangChain chat model for the configured provider.

    Why a factory:
      - Single place to change provider configuration
      - Easy to mock in tests
      - Clear error if provider is misconfigured
    """
    def __init__(
        self,
        provider: LLMProvider,
        # Ollama
        ollama_base_url: Optional[str] = None,
        ollama_model: Optional[str] = "llama3.2",
        # OpenAI
        openai_api_key: Optional[str] = None,
        openai_model: Optional[str] = "gpt-4o-mini",
        # Azure OpenAI
        azure_openai_endpoint: Optional[str] = None,
        azure_openai_api_key: Optional[str] = None,
        azure_openai_deployment: Optional[str] = None,
        azure_openai_api_version: Optional[str] = "2024-02-01",
        # Anthropic
        anthropic_api_key: Optional[str] = None,
        anthropic_model: Optional[str] = "claude-3-5-haiku-20241022",
    ) -> None:
        self.provider = provider
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.azure_openai_endpoint = azure_openai_endpoint
        self.azure_openai_api_key = azure_openai_api_key
        self.azure_openai_deployment = azure_openai_deployment
        self.azure_openai_api_version = azure_openai_api_version
        self.anthropic_api_key = anthropic_api_key
        self.anthropic_model = anthropic_model
    def create(self) -> BaseChatModel:
        """
        Create and return the configured LLM provider.

        Uses Python 3.12 match statement for clean dispatch.
        Fails immediately with clear message if provider unknown.
        """
        match self.provider:
            case LLMProvider.OLLAMA:
                return ChatOllama(
                    base_url=self.ollama_base_url,
                    model=self.ollama_model,
                    temperature=0,      # deterministic output
                    format="json",      # always return JSON
                )

            case LLMProvider.OPENAI:
                return ChatOpenAI(
                    api_key=self.openai_api_key,
                    model=self.openai_model,
                    temperature=0,
                )

            case LLMProvider.AZURE_OPENAI:
                return AzureChatOpenAI(
                    azure_endpoint=self.azure_openai_endpoint,
                    api_key=self.azure_openai_api_key,
                    azure_deployment=self.azure_openai_deployment,
                    api_version=self.azure_openai_api_version,
                    temperature=0,
                )
            case LLMProvider.ANTHROPIC:
                return ChatAnthropic(
                    api_key=self.anthropic_api_key,
                    model=self.anthropic_model,
                    temperature=0,
                )

            case _:
                raise ValueError(
                    f"Unsupported LLM provider: {self.provider}. "
                    f"Valid options: {[p.value for p in LLMProvider]}"
                )  
    @classmethod
    def from_settings(cls, settings) -> "LLMFactory":
        """
        Create factory from Settings object.
        Used in production — reads all config from environment.
        """
        return cls(
            provider=settings.llm_provider,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            azure_openai_endpoint=settings.azure_openai_endpoint,
            azure_openai_api_key=settings.azure_openai_api_key,
            azure_openai_deployment=settings.azure_openai_deployment,
            azure_openai_api_version=settings.azure_openai_api_version,
            anthropic_api_key=settings.anthropic_api_key,
            anthropic_model=settings.anthropic_model,
        )
        
    


