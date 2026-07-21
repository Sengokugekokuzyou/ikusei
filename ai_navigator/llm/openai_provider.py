"""OpenAI text provider.

Lazy-imports the SDK so Phase 1 (mock) runs without `openai` installed.
Wire it up by setting ``providers.text = "openai"`` and OPENAI_API_KEY.
(Note: image generation, spec §46, will use OpenAI in a later phase.)
"""

from __future__ import annotations

import os

from .base import LLMError, LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
        try:
            import openai  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only when selected
            raise LLMError(
                "The 'openai' package is not installed. "
                "Run `pip install openai` or set providers.text = 'mock'."
            ) from exc
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise LLMError("OPENAI_API_KEY is not set (see .env.example).")
        self._client = openai.OpenAI(api_key=key)
        self._model = os.environ.get("OPENAI_MODEL", model)

    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.7) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system or "Reply with only what is asked."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""
