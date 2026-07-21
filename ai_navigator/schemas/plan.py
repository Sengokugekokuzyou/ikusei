"""Selected plan schema (spec §44 output).

The single artifact a human reviews before Phase 2. Answers: what video to make
today, candidate titles, why, for whom, against what, and on which sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .score import Verdict


@dataclass
class SelectedPlan:
    topic: str
    produced_at: str
    # The winning idea.
    idea_id: int
    working_title: str
    title_candidates: list[str] = field(default_factory=list)  # seeds for §31
    # Why this idea won over the other 9 (spec §44 "企画理由").
    rationale: str = ""
    target_viewer: str = ""
    comparison_targets: list[str] = field(default_factory=list)
    # Source URLs actually used, mirrored into sources.json.
    sources_used: list[str] = field(default_factory=list)
    score_total: int = 0
    verdict: Verdict = Verdict.DISCARD
    fact_score: int = 0
    # If no idea cleared the bar, the pipeline declines to produce (spec §11/§43).
    produce: bool = True
    decline_reason: str = ""
