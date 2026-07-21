"""Narration track assembly (spec §8).

Concatenates the per-unit WAVs on the timeline, inserting silence for each
unit's `pause_after`, to reconstruct the full narration as one WAV. Pure stdlib
(`wave`), so no ffmpeg/pydub needed for audio.
"""

from __future__ import annotations

import wave
from pathlib import Path

from ..schemas import VoiceManifest


def build_narration_wav(voice: VoiceManifest, report_dir: Path, out_path: Path) -> float:
    clips = voice.clips
    if not clips:
        return 0.0
    # Read params from the first clip; assume consistent across clips.
    first = report_dir / clips[0].audio_path
    with wave.open(str(first), "rb") as wf:
        nch, sampw, rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()

    silence_frame = b"\x00" * (sampw * nch)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as out:
        out.setnchannels(nch)
        out.setsampwidth(sampw)
        out.setframerate(rate)
        for clip in clips:
            path = report_dir / clip.audio_path
            if path.exists():
                with wave.open(str(path), "rb") as wf:
                    out.writeframes(wf.readframes(wf.getnframes()))
            gap = int(round(clip.pause_after * rate))
            if gap > 0:
                out.writeframes(silence_frame * gap)
    with wave.open(str(out_path), "rb") as wf:
        return round(wf.getnframes() / float(wf.getframerate()), 3)
