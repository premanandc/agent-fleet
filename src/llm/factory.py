"""LLM factory for creating provider-agnostic chat models."""

import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

LLMProvider = Literal["openai", "anthropic"]


class LLMFactory:
    """Factory for creating LLM instances based on provider."""

    @staticmethod
    def create(
        provider: LLMProvider = "anthropic",
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> BaseChatModel:
        """
        Create an LLM instance based on the specified provider.

        Args:
            provider: The LLM provider to use ("openai" or "anthropic")
            model: Optional model name. If None, uses provider defaults
            temperature: Temperature for generation (0.0 - 1.0)
            **kwargs: Additional provider-specific arguments

        Returns:
            BaseChatModel instance configured for the specified provider

        Raises:
            ValueError: If provider is not supported or required API keys are missing
        """
        if provider == "openai":
            api_key = kwargs.pop("api_key", None) or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment or kwargs"
                )

            return ChatOpenAI(
                model=model or "gpt-4o",
                temperature=temperature,
                api_key=api_key,
                **kwargs,
            )

        elif provider == "anthropic":
            api_key = kwargs.pop("api_key", None) or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not found in environment or kwargs"
                )

            return ChatAnthropic(
                model=model or "claude-3-5-sonnet-20241022",
                temperature=temperature,
                api_key=api_key,
                **kwargs,
            )

        else:
            raise ValueError(
                f"Unsupported provider: {provider}. Choose 'openai' or 'anthropic'"
            )
