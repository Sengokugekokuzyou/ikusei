"""Scorer / Scoring engine (spec §11).

Turns each idea into an 8-axis breakdown on a 100-point scale. The per-axis
maxima come from config ``planner.score_weights`` (must sum to 100); the scorer
clamps the provider's numbers into range and computes the total. Verdict
assignment is the Judge's job (next stage).
"""

from __future__ import annotations

from ..llm import LLMProvider
from ..schemas import (
    CritiqueSet,
    IdeaSet,
    ScoreBreakdown,
    ScoredIdea,
    ScoreSet,
)

_AXES = [
    "beginner_value",
    "practicality",
    "search_demand",
    "topicality",
    "comparison_need",
    "video_appeal",
    "differentiation",
    "info_reliability",
]


class Scorer:
    def __init__(self, llm: LLMProvider, weights: dict[str, int]) -> None:
        self._llm = llm
        self._weights = {a: int(weights.get(a, 0)) for a in _AXES}
        total = sum(self._weights.values())
        if total != 100:
            raise ValueError(f"score_weights must sum to 100, got {total}: {self._weights}")

    def run(self, idea_set: IdeaSet, critiques: CritiqueSet) -> ScoreSet:
        crit_by_id = {c.idea_id: c for c in critiques.critiques}
        scored: list[ScoredIdea] = []
        for idea in idea_set.ideas:
            crit = crit_by_id.get(idea.id)
            prompt = (
                "次の動画案を100点満点で採点してください。配点は "
                "初心者価値25/実用性20/検索需要15/話題性10/比較需要10/動画映え10/"
                "差別化5/情報信頼性5。breakdown(各軸int)とrationaleを含むJSONで返答。\n"
                f"タイトル: {idea.title}\n狙い: {idea.viewer_takeaway}\n"
                f"欠点: {', '.join(crit.weaknesses[:3]) if crit else ''}"
            )
            data = self._llm.generate_json(
                prompt,
                task="score",
                context={
                    "idea": {
                        "id": idea.id,
                        "title": idea.title,
                        "viewer_takeaway": idea.viewer_takeaway,
                        "comparison_targets": idea.comparison_targets,
                    },
                    "weaknesses": crit.weaknesses if crit else [],
                },
            )
            raw = data.get("breakdown", {})
            clamped = {
                a: max(0, min(int(raw.get(a, 0)), self._weights[a])) for a in _AXES
            }
            breakdown = ScoreBreakdown(**clamped)
            scored.append(
                ScoredIdea(
                    idea_id=idea.id,
                    title=idea.title,
                    breakdown=breakdown,
                    total=breakdown.total(),
                    rationale=data.get("rationale", ""),
                )
            )
        return ScoreSet(topic=idea_set.topic, scored=scored)
