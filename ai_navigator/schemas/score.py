"""Scoring + Judge schemas (spec §11).

100-point scale across 8 weighted axes. The Judge maps the total to a verdict:
  >= 80        -> full video candidate
  65 .. 79     -> Shorts candidate
  <= 64        -> discard
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    VIDEO = "video"      # 通常動画候補
    SHORTS = "shorts"    # Shorts候補
    DISCARD = "discard"  # 廃棄


@dataclass
class ScoreBreakdown:
    """Per-axis points. Field names match config [planner.score_weights]."""

    beginner_value: int = 0    # /25
    practicality: int = 0      # /20
    search_demand: int = 0     # /15
    topicality: int = 0        # /10
    comparison_need: int = 0   # /10
    video_appeal: int = 0      # /10
    differentiation: int = 0   # /5
    info_reliability: int = 0  # /5

    def total(self) -> int:
        return (
            self.beginner_value
            + self.practicality
            + self.search_demand
            + self.topicality
            + self.comparison_need
            + self.video_appeal
            + self.differentiation
            + self.info_reliability
        )


@dataclass
class ScoredIdea:
    idea_id: int
    title: str
    breakdown: ScoreBreakdown
    total: int = 0
    verdict: Verdict = Verdict.DISCARD
    rationale: str = ""


@dataclass
class ScoreSet:
    topic: str
    scored: list[ScoredIdea] = field(default_factory=list)

    def ranked(self) -> list[ScoredIdea]:
        return sorted(self.scored, key=lambda s: s.total, reverse=True)
