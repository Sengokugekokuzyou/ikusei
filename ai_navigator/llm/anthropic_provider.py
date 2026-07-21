"""Anthropic (Claude) text provider — recommended for reasoning/generation.

Lazy-imports the SDK so Phase 1 (mock) runs without `anthropic` installed.
Wire it up by setting ``providers.text = "anthropic"`` and ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import os

from .base import LLMError, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-opus-4-8", api_key: str | None = None) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only when selected
            raise LLMError(
                "The 'anthropic' package is not installed. "
                "Run `pip install anthropic` or set providers.text = 'mock'."
            ) from exc
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set (see .env.example).")
        self._client = anthropic.Anthropic(api_key=key)
        self._model = os.environ.get("ANTHROPIC_MODEL", model)

    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.7) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            temperature=temperature,
            system=system or "You are a careful assistant. Reply with only what is asked.",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")
