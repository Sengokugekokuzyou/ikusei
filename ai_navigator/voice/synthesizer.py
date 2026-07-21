"""Voice Synthesizer (spec §7/§8).

Runs every TTS unit through the selected adapter, writes one WAV per unit, and
lays them on a single timeline (with §8 pauses) so subtitles and the storyboard
share exact timing.
"""

from __future__ import annotations

from pathlib import Path

from ..schemas import TTSScript, VoiceClip, VoiceManifest
from .base import VoiceAdapter


class VoiceSynthesizer:
    def __init__(self, adapter: VoiceAdapter) -> None:
        self._adapter = adapter

    def run(self, tts: TTSScript, out_dir: Path) -> VoiceManifest:
        voice_dir = out_dir / "voice"
        cursor = 0.0
        clips: list[VoiceClip] = []
        for unit in tts.units:
            rel = f"voice/unit_{unit.id:03d}.wav"
            duration = self._adapter.synthesize(
                unit.text, speed=unit.speed, out_path=out_dir / rel
            )
            start = round(cursor, 3)
            end = round(start + duration, 3)
            clips.append(
                VoiceClip(
                    id=unit.id,
                    section=unit.section,
                    line=unit.line,
                    text=unit.text,
                    start=start,
                    end=end,
                    duration=duration,
                    pause_after=unit.pause_after,
                    audio_path=rel,
                )
            )
            cursor = end + unit.pause_after
        return VoiceManifest(
            topic=tts.topic,
            produced_at=tts.produced_at,
            adapter=self._adapter.name,
            total_duration=round(cursor, 3),
            clips=clips,
        )
