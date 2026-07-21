"""Idea Generator (spec §9).

Produces at least N (default 10) distinct video ideas per topic, aimed at the
beginner audience and framed around a concrete decision the viewer can make.
"""

from __future__ import annotations

from ..llm import LLMProvider
from ..schemas import Idea, IdeaSet, ResearchReport


class IdeaGenerator:
    def __init__(self, llm: LLMProvider, ideas_per_topic: int = 10) -> None:
        self._llm = llm
        self._n = ideas_per_topic

    def run(self, topic: str, tools: list[str], research: ResearchReport) -> IdeaSet:
        prompt = (
            f"AI初心者向けチャンネルの企画会議です。トピック『{topic}』について、"
            f"切り口の異なる動画案を最低{self._n}本、JSON配列 ideas として出してください。"
            "各案は id,title,angle,description,target_viewer,comparison_targets,"
            "viewer_takeaway を含み、視聴後に『何を選べばいいか/どう使えばいいか』が"
            "分かる構成にすること。ニュース読み上げやベンチ数値の羅列は禁止。"
        )
        data = self._llm.generate_json(
            prompt,
            task="ideas",
            context={
                "topic": topic,
                "tools": tools,
                "n": self._n,
                "beginner_questions": research.beginner_questions,
            },
        )
        ideas = [
            Idea(
                id=int(i.get("id", n + 1)),
                title=i.get("title", ""),
                angle=i.get("angle", ""),
                description=i.get("description", ""),
                target_viewer=i.get("target_viewer", ""),
                comparison_targets=list(i.get("comparison_targets", [])),
                viewer_takeaway=i.get("viewer_takeaway", ""),
            )
            for n, i in enumerate(data.get("ideas", []))
        ]
        return IdeaSet(topic=topic, ideas=ideas)
