"""Script Writer (spec §17).

Turns the selected plan into a §17-structured script. Jargon in each line is
tagged with the Beginner Translator so TTS emphasis and beginner QA have signal.
The writer keeps sections in the canonical §17 order.
"""

from __future__ import annotations

from ..llm import LLMProvider
from ..research import BeginnerTranslator
from ..schemas import (
    ResearchReport,
    Script,
    ScriptLine,
    ScriptSection,
    SelectedPlan,
)
from ..schemas.script import SECTION_ORDER


class ScriptWriter:
    def __init__(self, llm: LLMProvider, tool_db: dict, translator: BeginnerTranslator | None = None) -> None:
        self._llm = llm
        self._tool_db = tool_db
        self._translator = translator or BeginnerTranslator()

    def _explain_jargon(self, sections: list[ScriptSection]) -> None:
        """Add a plain-language sentence for each jargon term (spec §19).

        Reads better as narration than inline parentheticals, and gives the
        Beginner QA a concrete explanation to detect.
        """
        full = "\n".join(l.text for sec in sections for l in sec.lines)
        gloss = self._translator._glossary
        seen: list[str] = []
        for sec in sections:
            for line in sec.lines:
                for term in line.jargon:
                    if term not in seen and gloss.get(term, "") not in full:
                        seen.append(term)
        if not seen:
            return
        target = next((s for s in sections if s.section == "beginner_explanation"), None)
        if target is None:
            target = ScriptSection(section="beginner_explanation", lines=[])
            sections.insert(min(1, len(sections)), target)
        for term in seen:
            target.lines.append(
                ScriptLine(text=f"『{term}』とは、{gloss[term]}のことです。", jargon=[term])
            )

    def run(self, plan: SelectedPlan, research: ResearchReport) -> Script:
        prompt = (
            "AI初心者向けの解説動画の台本を作ってください。構成は必ず "
            "Opening(15秒以内に誰なら何を使えばいいか一部先出し)→初心者向け概要→"
            "できること→実演→比較→向いてる人→向いてない人→結論(必ず言い切る) の順。"
            "『用途によります』のような濁した結論は禁止(§18)。"
            "sections[{section, lines[{text,is_claim}]}] のJSONで返答。\n"
            f"タイトル: {plan.working_title}\n比較対象: {', '.join(plan.comparison_targets)}"
        )
        data = self._llm.generate_json(
            prompt,
            task="script",
            context={
                "plan": {
                    "working_title": plan.working_title,
                    "comparison_targets": plan.comparison_targets,
                    "target_viewer": plan.target_viewer,
                },
                "tools": plan.comparison_targets,
                "tool_db": self._tool_db,
            },
        )
        by_name = {s.get("section"): s for s in data.get("sections", [])}
        sections: list[ScriptSection] = []
        for name in SECTION_ORDER:
            raw = by_name.get(name)
            if not raw:
                continue
            lines = [
                ScriptLine(
                    text=ln.get("text", ""),
                    jargon=self._translator.find_terms(ln.get("text", "")),
                    is_claim=bool(ln.get("is_claim", False)),
                )
                for ln in raw.get("lines", [])
                if ln.get("text")
            ]
            if lines:
                sections.append(ScriptSection(section=name, lines=lines))

        self._explain_jargon(sections)
        return Script(
            topic=plan.topic,
            produced_at=plan.produced_at,
            idea_id=plan.idea_id,
            working_title=plan.working_title,
            target_viewer=plan.target_viewer,
            comparison_targets=plan.comparison_targets,
            sections=sections,
        )
