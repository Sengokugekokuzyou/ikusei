"""Critic (spec §10).

For every idea, surface at least ``min_weaknesses_per_idea`` (default 5)
weaknesses across the evaluation axes. Forcing the pipeline to articulate flaws
before scoring keeps weak-but-shiny ideas from slipping through.
"""

from __future__ import annotations

from ..llm import LLMProvider
from ..schemas import Critique, CritiqueSet, IdeaSet
from ..schemas.critique import CRITIQUE_AXES


class Critic:
    def __init__(self, llm: LLMProvider, min_weaknesses: int = 5) -> None:
        self._llm = llm
        self._min = min_weaknesses

    def run(self, idea_set: IdeaSet) -> CritiqueSet:
        critiques: list[Critique] = []
        for idea in idea_set.ideas:
            prompt = (
                f"次の動画案の欠点を最低{self._min}個、辛口で挙げてください。"
                f"評価軸: {', '.join(CRITIQUE_AXES)}。"
                "weaknesses(配列)とaxis_notes(軸→短評)を含むJSONで返答。\n"
                f"タイトル: {idea.title}\n切り口: {idea.angle}"
            )
            data = self._llm.generate_json(
                prompt,
                task="critique",
                context={
                    "idea": {
                        "id": idea.id,
                        "title": idea.title,
                        "angle": idea.angle,
                        "comparison_targets": idea.comparison_targets,
                    },
                    "min": self._min,
                },
            )
            weaknesses = list(data.get("weaknesses", []))
            # Enforce the §10 floor so no idea escapes with too little scrutiny.
            while len(weaknesses) < self._min:
                weaknesses.append("(要追記) さらなる欠点の洗い出しが必要")
            critiques.append(
                Critique(
                    idea_id=idea.id,
                    weaknesses=weaknesses,
                    axis_notes=dict(data.get("axis_notes", {})),
                )
            )
        return CritiqueSet(topic=idea_set.topic, critiques=critiques)
