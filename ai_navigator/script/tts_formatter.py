"""TTS Formatter (spec §8).

Converts the script into narration units — the script is shaped, not read
verbatim: sentences are split, emphasis is set on jargon/tool names, and a
longer pause is inserted at section boundaries.
"""

from __future__ import annotations

import re

from ..schemas import AudioUnit, Script, TTSScript

_SENT_SPLIT = re.compile(r"(?<=[。！？])")


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


class TTSFormatter:
    def __init__(self, base_speed: float = 1.03) -> None:
        self._speed = base_speed

    def run(self, script: Script) -> TTSScript:
        units: list[AudioUnit] = []
        uid = 0
        line_idx = -1
        tools = script.comparison_targets
        for sec in script.sections:
            last_line = len(sec.lines) - 1
            for li, line in enumerate(sec.lines):
                line_idx += 1
                sentences = split_sentences(line.text)
                for si, sentence in enumerate(sentences):
                    uid += 1
                    end_of_section = li == last_line and si == len(sentences) - 1
                    emphasis = list(line.jargon)
                    for t in tools:
                        if t and t in sentence and t not in emphasis:
                            emphasis.append(t)
                    emotion = "confident" if sec.section == "final_decision" else "friendly"
                    units.append(
                        AudioUnit(
                            id=uid,
                            section=sec.section,
                            text=sentence,
                            line=line_idx,
                            speaker="default",
                            speed=self._speed,
                            pause_after=0.6 if end_of_section else 0.35,
                            emotion=emotion,
                            emphasis=emphasis,
                        )
                    )
        return TTSScript(topic=script.topic, produced_at=script.produced_at, units=units)
