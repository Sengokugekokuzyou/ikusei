"""Voice adapter interface (spec §7).

Same pattern as the LLM layer: stages depend on one interface, the backend is
config-selected. The `mock` adapter needs no VOICEVOX engine — it writes a
silent placeholder WAV of the estimated length so the whole timeline (subtitles,
storyboard durations) is real and offline-verifiable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

# Rough JP narration pace: seconds of speech per character at speed 1.0.
# ~7.5 chars/sec is a natural VOICEVOX-ish default for explainer narration.
_SEC_PER_CHAR = 0.133


def estimate_duration(text: str, speed: float = 1.0) -> float:
    """Estimate speech length in seconds (excludes trailing pause)."""
    chars = len(text.strip())
    base = max(0.4, chars * _SEC_PER_CHAR)
    return round(base / max(0.5, speed), 3)


class VoiceAdapter(ABC):
    name = "base"

    @abstractmethod
    def synthesize(self, text: str, *, speed: float, out_path: Path) -> float:
        """Write audio to out_path and return its duration in seconds."""


def build_adapter(
    name: str, *, sample_rate: int = 24000, endpoint: str = "", speaker: int = 3
) -> VoiceAdapter:
    name = (name or "mock").lower()
    if name == "mock":
        from .mock import MockVoiceAdapter

        return MockVoiceAdapter(sample_rate=sample_rate)
    if name == "voicevox":
        from .voicevox import VoicevoxAdapter

        return VoicevoxAdapter(endpoint=endpoint, speaker=speaker)
    raise ValueError(f"Unknown voice adapter: {name!r} (expected mock/voicevox)")
