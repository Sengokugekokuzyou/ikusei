"""Plan pipeline (spec §39 Phase 1, §44).

Wires the stages together:

    research -> fact-check -> ideas(>=10) -> critique -> score -> judge

and writes the six report artifacts a human reviews before Phase 2:

    reports/YYYY-MM-DD_<slug>/
      research.json  ideas.json  critique.json
      scores.json    selected_plan.json  sources.json
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path

from .config import Config
from .database import ToolDatabase
from .llm import build_provider
from .planner import Critic, IdeaGenerator, Judge, Scorer
from .research import FactChecker, Researcher, extract_tools
from .schemas import SelectedPlan, to_json


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

    @staticmethod
    def _write(path: Path, obj) -> None:
        path.write_text(to_json(obj) + "\n", encoding="utf-8")
