"""Mock voice adapter — writes a silent WAV of the estimated length.

No VOICEVOX engine required. The silent clip is a real, playable file so later
phases (FFmpeg concat, Remotion audio sync) have concrete inputs, and the
timeline is deterministic and offline.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from .base import VoiceAdapter, estimate_duration


class MockVoiceAdapter(VoiceAdapter):
    name = "mock"

    def __init__(self, sample_rate: int = 24000) -> None:
        self._rate = sample_rate

    def synthesize(self, text: str, *, speed: float, out_path: Path) -> float:
        duration = estimate_duration(text, speed)
        frames = int(duration * self._rate)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self._rate)
            wf.writeframes(struct.pack("<h", 0) * frames)
        return duration
