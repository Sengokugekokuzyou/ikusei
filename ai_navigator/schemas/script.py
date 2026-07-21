"""Script + TTS schemas (spec §17, §8).

The script is structured by the fixed §17 section order (not free prose) so
downstream QA can check each part, and the final decision is guaranteed to
exist. TTS units follow the §8 format so narration is shaped, never read
verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Fixed section order from spec §17.
SECTION_ORDER = [
    "opening",              # 15秒以内に「誰なら何を使えばいいか」一部先出し
    "beginner_explanation", # 専門用語抜きで概要
    "what_can_it_do",       # 具体的にできること
    "real_demo",            # 実際の画面（capture placeholder in Phase 2）
    "comparison",           # 他AIとの違い
    "recommended_for",      # 向いている人
    "not_recommended_for",  # 向いていない人
    "final_decision",       # 必ず結論
]

SECTION_LABELS = {
    "opening": "オープニング",
    "beginner_explanation": "初心者向け概要",
    "what_can_it_do": "何ができる？",
    "real_demo": "実演",
    "comparison": "比較",
    "recommended_for": "向いている人",
    "not_recommended_for": "向いていない人",
    "final_decision": "結論",
}


@dataclass
class ScriptLine:
    text: str
    # Terms flagged as jargon (drives emphasis + beginner QA).
    jargon: list[str] = field(default_factory=list)
    # True for lines that assert a checkable fact (drives fact QA).
    is_claim: bool = False


@dataclass
class ScriptSection:
    section: str  # one of SECTION_ORDER
    lines: list[ScriptLine] = field(default_factory=list)


@dataclass
class Script:
    topic: str
    produced_at: str
    idea_id: int
    working_title: str
    target_viewer: str = ""
    comparison_targets: list[str] = field(default_factory=list)
    sections: list[ScriptSection] = field(default_factory=list)

    def full_text(self) -> str:
        return "\n".join(
            line.text for sec in self.sections for line in sec.lines
        )

    def section(self, name: str) -> ScriptSection | None:
        for sec in self.sections:
            if sec.section == name:
                return sec
        return None


@dataclass
class AudioUnit:
    """One narration unit (spec §8)."""

    id: int
    section: str
    text: str
    line: int = 0  # global script-line index this unit came from
    speaker: str = "default"
    speed: float = 1.0
    pause_after: float = 0.3
    emotion: str = "friendly"
    emphasis: list[str] = field(default_factory=list)


@dataclass
class TTSScript:
    topic: str
    produced_at: str
    units: list[AudioUnit] = field(default_factory=list)
