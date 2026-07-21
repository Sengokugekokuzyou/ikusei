"""LLM provider factory."""

from __future__ import annotations

from typing import Any

from .base import LLMError, LLMProvider
from .mock import MockProvider

__all__ = ["LLMProvider", "LLMError", "MockProvider", "build_provider"]


def build_provider(
    name: str,
    *,
    model: str = "",
    tool_db: dict[str, Any] | None = None,
) -> LLMProvider:
    """Instantiate the text provider selected in config.

    ``tool_db`` is only used by the mock (as its knowledge base).
    """
    name = (name or "mock").lower()
    if name == "mock":
        return MockProvider(tool_db=tool_db)
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model or "claude-opus-4-8")
    if name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model=model or "gpt-4o")
    raise LLMError(f"Unknown provider: {name!r} (expected mock/anthropic/openai)")
