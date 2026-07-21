"""Voice stage (spec §7 VOICEVOX, §8 audio design)."""

from .base import VoiceAdapter, estimate_duration, build_adapter
from .synthesizer import VoiceSynthesizer

__all__ = ["VoiceAdapter", "estimate_duration", "build_adapter", "VoiceSynthesizer"]
