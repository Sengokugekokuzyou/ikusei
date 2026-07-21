"""Plan pipeline (spec §39 Phase 1, §44).

Wires the stages together:

    research -> fact-check -> ideas(>=10) -> critique -> score -> judge

and writes the six report artifacts a human reviews before Phase 2:

    reports/YYYY-MM-DD_<slug>/
      research.json  ideas.json  critique.json
      scores.json    selected_plan.json  sources.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from .config import Config
from .database import ToolDatabase
from .llm import build_provider
from .planner import Critic, IdeaGenerator, Judge, Scorer
from .research import BeginnerTranslator, FactChecker, Researcher, extract_tools
from .script import BeginnerQA, FactQA, ScriptWriter, TTSFormatter
from .schemas import (
    BeginnerQAReport,
    FactQAReport,
    Finding,
    ResearchReport,
    Script,
    SelectedPlan,
    Verdict,
    to_json,
)


def slugify(text: str) -> str:
    """ASCII slug when possible, else a safe fallback for report dir names."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    ascii_text = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return ascii_text or "topic"


class PlanPipeline:
    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._tool_db = ToolDatabase(config.tools_db_dir())
        tools_dict = self._tool_db.all()
        provider_name = config.get("providers.text", "mock")
        model = config.get(f"providers.models.{provider_name}", "")
        self._llm = build_provider(provider_name, model=model, tool_db=tools_dict)

    def run(self, topic: str, on_date: date | None = None) -> tuple[SelectedPlan, Path]:
        produced_at = (on_date or date.today()).isoformat()
        known = self._tool_db.known_tools()
        tools = extract_tools(topic, known)

        # 1) Research + fact-check
        researcher = Researcher(self._llm)
        research = researcher.run(topic, tools, produced_at)

        fact_checker = FactChecker(self._llm, self._tool_db.all())
        fact = fact_checker.run(topic, tools, produced_at)
        research.fact_check = fact

        # 2) Ideas (>=10) -> critique -> score -> judge
        generator = IdeaGenerator(self._llm, self._cfg.get("planner.ideas_per_topic", 10))
        idea_set = generator.run(topic, tools, research)

        critic = Critic(self._llm, self._cfg.get("planner.min_weaknesses_per_idea", 5))
        critique_set = critic.run(idea_set)

        scorer = Scorer(self._llm, self._cfg.get("planner.score_weights", {}))
        score_set = scorer.run(idea_set, critique_set)

        judge = Judge(
            video_min=self._cfg.get("planner.judge.video_min", 80),
            shorts_min=self._cfg.get("planner.judge.shorts_min", 65),
            min_fact_score=self._cfg.get("fact_check.min_fact_score", 95),
        )
        plan = judge.run(topic, produced_at, idea_set, score_set, research, fact)

        # 3) Write artifacts
        out_dir = self._cfg.report_root() / f"{produced_at}_{slugify(topic)}"
        out_dir.mkdir(parents=True, exist_ok=True)
        self._write(out_dir / "research.json", research)
        self._write(out_dir / "ideas.json", idea_set)
        self._write(out_dir / "critique.json", critique_set)
        self._write(out_dir / "scores.json", score_set)
        self._write(out_dir / "selected_plan.json", plan)
        self._write(
            out_dir / "sources.json",
            {"topic": topic, "produced_at": produced_at, "sources": research.sources},
        )
        return plan, out_dir

    # --- Phase 2: Script system (§17/§8/§20/§13) ---------------------------
    def build_script(
        self, plan: SelectedPlan, research: ResearchReport
    ) -> tuple[Script, BeginnerQAReport, FactQAReport, "TTSScriptType"]:
        translator = BeginnerTranslator()
        tool_db = self._tool_db.all()
        writer = ScriptWriter(self._llm, tool_db, translator)
        beginner_qa = BeginnerQA(threshold=80, translator=translator)
        fact_qa = FactQA(tool_db, threshold=self._cfg.get("fact_check.min_fact_score", 95))
        formatter = TTSFormatter()

        # Regeneration loop (§20/§30): rewrite until beginner QA clears the bar.
        max_attempts = 3
        script = writer.run(plan, research)
        bqa = beginner_qa.run(script, attempts=1)
        attempt = 1
        while not bqa.passed and attempt < max_attempts:
            attempt += 1
            script = writer.run(plan, research)
            bqa = beginner_qa.run(script, attempts=attempt)

        fqa = fact_qa.run(script, research)
        tts = formatter.run(script)
        return script, bqa, fqa, tts

    def run_script_from_dir(self, report_dir: Path) -> tuple[Script, BeginnerQAReport, FactQAReport]:
        plan = _load_plan(report_dir / "selected_plan.json")
        research = _load_research(report_dir / "research.json")
        script, bqa, fqa, tts = self.build_script(plan, research)
        self._write(report_dir / "script.json", script)
        self._write(report_dir / "script_tts.json", tts)
        self._write(report_dir / "beginner_qa.json", bqa)
        self._write(report_dir / "fact_qa.json", fqa)
        return script, bqa, fqa

    @staticmethod
    def _write(path: Path, obj) -> None:
        path.write_text(to_json(obj) + "\n", encoding="utf-8")


# Type alias used only for the return annotation above.
from .schemas import TTSScript as TTSScriptType  # noqa: E402


def _load_plan(path: Path) -> SelectedPlan:
    d = json.loads(path.read_text(encoding="utf-8"))
    d["verdict"] = Verdict(d.get("verdict", "discard"))
    return SelectedPlan(**d)


def _load_research(path: Path) -> ResearchReport:
    d = json.loads(path.read_text(encoding="utf-8"))
    findings = [
        Finding(
            claim=f.get("claim", ""),
            detail=f.get("detail", ""),
            source_urls=list(f.get("source_urls", [])),
            kind=f.get("kind", "fact"),
        )
        for f in d.get("findings", [])
    ]
    # FactQA only needs topic + findings; keep the loader minimal.
    return ResearchReport(
        topic=d.get("topic", ""),
        produced_at=d.get("produced_at", ""),
        tools_covered=list(d.get("tools_covered", [])),
        findings=findings,
    )
