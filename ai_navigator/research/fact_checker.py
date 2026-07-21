"""Fact Checker (spec §13).

Verifies concrete attributes (pricing, free plan, API, versions, JP support …)
against official sources, records the production date in metadata, and emits a
0–100 fact score. The Judge/pipeline fails a plan whose fact score is below
``fact_check.min_fact_score`` (default 95).
"""

from __future__ import annotations

from ..llm import LLMProvider
from ..schemas import FactCheckItem, FactCheckReport


class FactChecker:
    def __init__(self, llm: LLMProvider, tool_db: dict) -> None:
        self._llm = llm
        self._tool_db = tool_db

    def run(self, topic: str, tools: list[str], produced_at: str) -> FactCheckReport:
        prompt = (
            "次のAIツールについて、公開日/料金/対応OS/無料プラン有無/API有無/"
            "利用可能地域/日本語対応/商用利用/最新バージョンを、公式記載と一致するか"
            "検証し、items(field,tool,value,verified,matches_official,source_url,note)と"
            "fact_score(0-100)を含むJSONで返してください。\n"
            f"トピック: {topic}\n対象ツール: {', '.join(tools)}"
        )
        data = self._llm.generate_json(
            prompt,
            task="fact_check",
            context={"topic": topic, "tools": tools, "tool_db": self._tool_db},
        )
        items = [
            FactCheckItem(
                field=i.get("field", ""),
                tool=i.get("tool", ""),
                value=i.get("value", ""),
                verified=bool(i.get("verified", False)),
                matches_official=bool(i.get("matches_official", False)),
                source_url=i.get("source_url", ""),
                note=i.get("note", ""),
            )
            for i in data.get("items", [])
        ]
        return FactCheckReport(
            produced_at=produced_at,
            items=items,
            fact_score=int(data.get("fact_score", 0)),
            notes=list(data.get("notes", [])),
        )
