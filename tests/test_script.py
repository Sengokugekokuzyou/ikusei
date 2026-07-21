"""Phase 2 tests. Runs under pytest, or standalone: `python tests/test_script.py`."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_navigator.config import load_config
from ai_navigator.pipeline import PlanPipeline
from ai_navigator.script import BeginnerQA, FactQA, TTSFormatter
from ai_navigator.schemas import (
    ResearchReport,
    Script,
    ScriptLine,
    ScriptSection,
    Finding,
)


def _make_pipeline_and_plan():
    cfg = load_config()
    pipeline = PlanPipeline(cfg)
    plan, out_dir = pipeline.run("Claude Code vs Codex", on_date=date(2026, 7, 21))
    research = ResearchReport(topic=plan.topic, findings=[])
    return pipeline, plan, research, out_dir


def test_script_pipeline_passes_qa():
    pipeline, plan, _, out_dir = _make_pipeline_and_plan()
    # Load research back from disk (has findings) like the CLI does.
    _script, bqa, fqa = pipeline.run_script_from_dir(out_dir)
    assert bqa.passed, f"beginner QA failed: {bqa.score} {[i.detail for i in bqa.issues]}"
    assert fqa.passed, f"fact QA failed: {fqa.score} {[i.detail for i in fqa.issues]}"
    # §17: final decision must exist and be non-empty.
    final = _script.section("final_decision")
    assert final is not None and final.lines
    for name in ["script", "script_tts", "beginner_qa", "fact_qa"]:
        assert (out_dir / f"{name}.json").exists()


def test_tts_emphasises_tool_names():
    pipeline, plan, research, _ = _make_pipeline_and_plan()
    script, _bqa, _fqa, tts = pipeline.build_script(plan, research)
    assert len(tts.units) > 0
    joined = " ".join(u.text for u in tts.units)
    assert "Claude Code" in joined
    # At least one unit emphasises a tool name.
    assert any("Claude Code" in u.emphasis or "Codex" in u.emphasis for u in tts.units)


def test_beginner_qa_catches_hedged_conclusion():
    script = Script(
        topic="t", produced_at="2026-07-21", idea_id=1, working_title="x",
        comparison_targets=["A", "B"],
        sections=[
            ScriptSection("opening", [ScriptLine("こんにちは。")]),
            ScriptSection("final_decision", [ScriptLine("結局、用途によります。")]),
        ],
    )
    report = BeginnerQA().run(script)
    assert report.checks["clear_conclusion"] == 0
    assert any(i.check == "clear_conclusion" for i in report.issues)


def test_fact_qa_flags_unsupported_claim():
    script = Script(
        topic="t", produced_at="2026-07-21", idea_id=1, working_title="x",
        comparison_targets=[],
        sections=[
            ScriptSection("what_can_it_do", [
                ScriptLine("このAIは1秒で100万行のコードを書けます。", is_claim=True),
            ]),
        ],
    )
    research = ResearchReport(topic="t", findings=[])
    report = FactQA(tool_db={}).run(script, research)
    assert report.total_claims == 1
    assert report.supported_claims == 0
    assert not report.passed


def test_jargon_is_explained_in_script():
    pipeline, plan, research, _ = _make_pipeline_and_plan()
    script, _bqa, _fqa, _tts = pipeline.build_script(plan, research)
    text = script.full_text()
    # If "ターミナル" appears, its plain-language gloss must appear too (§19).
    if "ターミナル" in text:
        assert "文字でパソコンを操作する黒い画面" in text


def test_tts_sentence_split():
    from ai_navigator.script.tts_formatter import split_sentences
    assert split_sentences("あ。い！う？") == ["あ。", "い！", "う？"]
    assert split_sentences("区切りなし") == ["区切りなし"]


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
