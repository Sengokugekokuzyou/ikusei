"""Phase: Thumbnails. Runs under pytest, or standalone: `python tests/test_thumbnail.py`."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_navigator.config import load_config
from ai_navigator.pipeline import PlanPipeline
from ai_navigator.thumbnail import ThumbnailDirector, ThumbnailJudge, find_chrome
from ai_navigator.thumbnail.renderer import build_html
from ai_navigator.schemas import SelectedPlan, ThumbnailCandidate, ThumbnailSpec, Verdict


def _plan():
    return SelectedPlan(
        topic="Claude Code vs Codex", produced_at="2026-07-21", idea_id=10,
        working_title="Claude Code と Codex、あなたはこっち",
        comparison_targets=["Claude Code", "Codex"], verdict=Verdict.VIDEO,
    )


def test_director_produces_at_least_3_distinct():
    specs = ThumbnailDirector().run(_plan())
    assert len(specs) >= 3
    labels = [s.label for s in specs]
    assert labels[:3] == ["A", "B", "C"]
    # Distinct palettes (§64).
    assert len({s.bg_from for s in specs}) >= 3


def test_build_html_contains_headline_and_font():
    spec = ThumbnailDirector().run(_plan())[0]
    html = build_html(spec)
    assert "結局どっち？" in html
    assert "IPAGothic" in html or "IPAPGothic" in html
    assert "1280px" in html and "720px" in html


def test_judge_prefers_short_headline_and_correct_size():
    good = ThumbnailCandidate(spec=ThumbnailSpec(label="A", text="結局どっち？", subjects=["A", "B"], layout="split"), width=1280, height=720)
    wordy = ThumbnailCandidate(spec=ThumbnailSpec(label="B", text="これはとても長すぎる見出しの例文です", subjects=["A"], layout="question"), width=1280, height=720)
    judge = ThumbnailJudge()
    gs, _ = judge.score(good)
    ws, _ = judge.score(wordy)
    assert gs > ws
    assert judge.judge([good, wordy]) == "A"


def test_pipeline_thumbnails():
    cfg = load_config()
    pipeline = PlanPipeline(cfg)
    plan, _ = pipeline.run("Claude Code vs Codex", on_date=date(2026, 7, 21))
    out_dir = Path(tempfile.mkdtemp(prefix="ainav-thumb-"))
    result = pipeline.build_thumbnails(plan, out_dir)
    assert len(result.candidates) >= 3
    if find_chrome():
        # Chromium present: real PNGs at 1280x720 and a chosen candidate.
        assert result.chosen_label in {"A", "B", "C"}
        for c in result.candidates:
            assert (out_dir / c.image_path).exists()
            assert (c.width, c.height) == (1280, 720)
    else:
        assert result.warnings  # graceful degradation


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
