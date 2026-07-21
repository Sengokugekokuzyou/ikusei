"""Phase 1 tests. Runs under pytest, or standalone: `python tests/test_planning.py`."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_navigator.config import load_config
from ai_navigator.llm import MockProvider
from ai_navigator.pipeline import PlanPipeline, slugify
from ai_navigator.planner import Judge
from ai_navigator.research import BeginnerTranslator, extract_tools
from ai_navigator.schemas import (
    FactCheckReport,
    IdeaSet,
    ResearchReport,
    ScoreBreakdown,
    ScoreSet,
    ScoredIdea,
    Verdict,
)


def test_score_weights_sum_to_100():
    cfg = load_config()
    weights = cfg.get("planner.score_weights")
    assert sum(weights.values()) == 100


def test_score_breakdown_total():
    b = ScoreBreakdown(
        beginner_value=25, practicality=20, search_demand=15, topicality=10,
        comparison_need=10, video_appeal=10, differentiation=5, info_reliability=5,
    )
    assert b.total() == 100


def test_judge_thresholds():
    j = Judge(video_min=80, shorts_min=65, min_fact_score=95)
    assert j._verdict(83) == Verdict.VIDEO
    assert j._verdict(80) == Verdict.VIDEO
    assert j._verdict(79) == Verdict.SHORTS
    assert j._verdict(65) == Verdict.SHORTS
    assert j._verdict(64) == Verdict.DISCARD


def test_judge_declines_when_all_below_bar():
    j = Judge(video_min=80, shorts_min=65, min_fact_score=95)
    ideas = IdeaSet(topic="t", ideas=[])
    scores = ScoreSet(topic="t", scored=[
        ScoredIdea(idea_id=1, title="weak", breakdown=ScoreBreakdown(), total=50),
    ])
    plan = j.run("t", "2026-07-21", ideas, scores, ResearchReport(topic="t"), FactCheckReport())
    assert plan.produce is False
    assert "基準" in plan.decline_reason


def test_judge_declines_on_low_fact_score():
    j = Judge(video_min=80, shorts_min=65, min_fact_score=95)
    ideas = IdeaSet(topic="t", ideas=[])
    scores = ScoreSet(topic="t", scored=[
        ScoredIdea(idea_id=1, title="ok", breakdown=ScoreBreakdown(beginner_value=25), total=90),
    ])
    fact = FactCheckReport(fact_score=80)
    plan = j.run("t", "2026-07-21", ideas, scores, ResearchReport(topic="t"), fact)
    assert plan.produce is False
    assert "ファクト" in plan.decline_reason


def test_extract_tools_order():
    known = ["Claude Code", "Codex", "Kimi"]
    assert extract_tools("Codex vs Claude Code", known) == ["Codex", "Claude Code"]
    assert extract_tools("Kimiって何？", known) == ["Kimi"]


def test_beginner_translator_annotates_once():
    t = BeginnerTranslator()
    out = t.annotate("CLIでAPIを叩く。CLIは大事。")
    assert out.count("文字でパソコンに指示を出す画面") == 1  # only first CLI annotated
    assert "他のソフトからそのAIを呼び出すための窓口" in out


def test_pipeline_end_to_end(tmp_path=None):
    cfg = load_config()
    pipeline = PlanPipeline(cfg)
    plan, out_dir = pipeline.run("Claude Code vs Codex", on_date=date(2026, 7, 21))
    assert plan.produce is True
    assert plan.verdict == Verdict.VIDEO
    assert plan.comparison_targets == ["Claude Code", "Codex"]
    assert plan.fact_score == 100
    for name in ["research", "ideas", "critique", "scores", "selected_plan", "sources"]:
        assert (out_dir / f"{name}.json").exists()


def test_generator_min_ideas():
    cfg = load_config()
    from ai_navigator.planner import IdeaGenerator
    llm = MockProvider(tool_db={})
    gen = IdeaGenerator(llm, 10)
    ideas = gen.run("Claude Code vs Codex", ["Claude Code", "Codex"], ResearchReport(topic="x"))
    assert len(ideas.ideas) >= 10


def test_windows_batch_is_pure_ascii():
    # A .bat with non-ASCII bytes breaks cmd parsing on Japanese Windows (CP932)
    # and the window closes instantly. Keep make_video.bat ASCII-only.
    bat = Path(__file__).resolve().parent.parent / "scripts" / "make_video.bat"
    data = bat.read_bytes()
    bad = [(i, b) for i, b in enumerate(data) if b > 127]
    assert not bad, f"non-ASCII bytes in make_video.bat at offsets {[i for i, _ in bad[:5]]}"


def test_slugify():
    assert slugify("Claude Code vs Codex") == "claude-code-vs-codex"
    assert slugify("Kimiって何？") == "kimi"  # ascii kept, JP dropped
    assert slugify("これは何？") == "topic"  # fully non-ascii falls back


def _run_standalone() -> int:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
