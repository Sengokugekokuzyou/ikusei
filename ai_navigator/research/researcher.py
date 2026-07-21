"""Researcher (spec §12).

Gathers sources across the Tier 1–4 trust hierarchy and produces findings and
beginner questions. In Phase 1 the actual gathering is delegated to the LLM
provider (mock synthesises from the tool DB); later phases add real collectors
(official/news/youtube/reddit) behind the same interface.
"""

from __future__ import annotations

from ..llm import LLMProvider
from ..schemas import (
    Finding,
    ResearchReport,
    Source,
    SourceTier,
)


def extract_tools(topic: str, known_tools: list[str]) -> list[str]:
    """Find which known tools the topic mentions, preserving mention order."""
    hits: list[tuple[int, str]] = []
    lowered = topic.lower()
    for tool in known_tools:
        idx = lowered.find(tool.lower())
        if idx != -1:
            hits.append((idx, tool))
    hits.sort(key=lambda x: x[0])
    return [t for _, t in hits]


class Researcher:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def run(self, topic: str, tools: list[str], produced_at: str) -> ResearchReport:
        prompt = (
            "あなたはAI解説チャンネルのリサーチャーです。次のトピックについて、"
            "公式(Tier1)を最優先に、信頼できるTech Media(Tier2)、YouTube(Tier3)を根拠に、"
            "Reddit/X(Tier4)は『ユーザーの反応・困りごと』としてのみ扱い、"
            "sources / findings / beginner_questions を含むJSONを返してください。\n"
            f"トピック: {topic}\n対象ツール: {', '.join(tools) or '(不明)'}"
        )
        data = self._llm.generate_json(
            prompt,
            task="research",
            context={"topic": topic, "tools": tools},
        )
        sources = [
            Source(
                title=s.get("title", ""),
                url=s.get("url", ""),
                tier=SourceTier(int(s.get("tier", 1))),
                publisher=s.get("publisher", ""),
                published_at=s.get("published_at", ""),
            )
            for s in data.get("sources", [])
        ]
        findings = [
            Finding(
                claim=f.get("claim", ""),
                detail=f.get("detail", ""),
                source_urls=list(f.get("source_urls", [])),
                kind=f.get("kind", "fact"),
            )
            for f in data.get("findings", [])
        ]
        return ResearchReport(
            topic=topic,
            produced_at=produced_at,
            tools_covered=data.get("tools_covered", tools),
            sources=sources,
            findings=findings,
            beginner_questions=list(data.get("beginner_questions", [])),
        )
