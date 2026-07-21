"""LLM provider interface.

Pipeline stages depend only on this interface, never on a concrete SDK. Swapping
``providers.text`` in config between "mock" / "anthropic" / "openai" changes the
backend with zero code changes elsewhere (see the proposal in the PR/README).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    """Minimal surface the pipeline needs: text in, (optionally JSON) text out."""

    name: str = "base"

    @abstractmethod
    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.7) -> str:
        """Return a plain-text completion."""

    def generate_json(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.4,
        task: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Return parsed JSON. Default impl asks for JSON then parses it.

        ``task``/``context`` are hints. Real providers ignore them and rely on
        ``prompt``; the deterministic MockProvider routes on ``task`` to
        synthesise plausible structured output without any API call.
        """
        raw = self.complete(prompt, system=system, temperature=temperature)
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(raw: str) -> Any:
        """Best-effort JSON extraction from a model response."""
        raw = raw.strip()
        if raw.startswith("```"):
            # strip ```json ... ``` fences
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip("` \n")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw[start : end + 1])
            raise LLMError(f"Could not parse JSON from response: {raw[:200]!r}")
