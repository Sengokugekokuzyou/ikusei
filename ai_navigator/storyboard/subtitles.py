"""Subtitle track (spec §28).

One subtitle per narration unit, timed to the voice manifest. Important words
(tool names / jargon) are carried in `emphasis` so the renderer can highlight
them rather than showing the whole line as a large caption.
"""

from __future__ import annotations

from ..schemas import Subtitle, SubtitleTrack, TTSScript, VoiceManifest


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(track: SubtitleTrack) -> str:
    blocks = []
    for sub in track.subtitles:
        blocks.append(
            f"{sub.index}\n{_fmt_ts(sub.start)} --> {_fmt_ts(sub.end)}\n{sub.text}"
        )
    return "\n\n".join(blocks) + "\n"


class SubtitleBuilder:
    def run(self, tts: TTSScript, voice: VoiceManifest) -> SubtitleTrack:
        emphasis_by_id = {u.id: u.emphasis for u in tts.units}
        subs = [
            Subtitle(
                index=i,
                start=clip.start,
                end=clip.end,
                text=clip.text,
                emphasis=list(emphasis_by_id.get(clip.id, [])),
            )
            for i, clip in enumerate(voice.clips, start=1)
        ]
        return SubtitleTrack(topic=tts.topic, produced_at=tts.produced_at, subtitles=subs)
