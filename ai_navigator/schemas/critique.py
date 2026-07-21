"""Critic schema (spec §10).

Each idea gets at least 5 weaknesses, assessed against the evaluation axes:
competition strength, beginner fit, whether a conclusion is possible, video
appeal, information value, long-term searchability, and mass-produced feel.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The evaluation axes from spec §10, used to prompt the critic and to tag
# weaknesses so downstream scoring can see *why* an idea is weak.
CRITIQUE_AXES = [
    "competition_too_strong",   # 競合が強すぎないか
    "beginner_fit",             # 初心者向けか
    "conclusion_possible",      # 結論が出せるか
    "video_appeal",             # 動画映えするか
    "information_value",        # 情報価値があるか
    "long_term_search",         # 長期検索されるか
    "not_mass_produced",        # 量産AI動画に見えないか
]


@dataclass
class Critique:
    idea_id: int
    weaknesses: list[str] = field(default_factory=list)  # >= 5 (spec §10)
    # Optional per-axis notes keyed by an entry of CRITIQUE_AXES.
    axis_notes: dict[str, str] = field(default_factory=dict)


@dataclass
class CritiqueSet:
    topic: str
    critiques: list[Critique] = field(default_factory=list)
