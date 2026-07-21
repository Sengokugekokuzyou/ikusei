"""Phase 5 (capture) tests. Standalone: `python tests/test_capture.py`.

The recording step is guarded on Playwright/Chromium/ffmpeg availability so the
suite still passes without them.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_navigator.capture import CaptureRecorder, placeholder_recipe, playwright_available
from ai_navigator.config import load_config
from ai_navigator.pipeline import PlanPipeline


def test_placeholder_recipe_is_safe_and_scripted():
    tmp = Path(tempfile.mkdtemp(prefix="ainav-cap-"))
    recipe = placeholder_recipe(tmp, scene_id=12)
    assert recipe.is_real_service is False           # §49: not a real service
    assert recipe.url.startswith("file://")
    assert (tmp / "capture_src" / "demo.html").exists()
    kinds = [a.kind for a in recipe.actions]
    assert "type" in kinds and "click" in kinds       # scripted operation
    html = (tmp / "capture_src" / "demo.html").read_text(encoding="utf-8")
    assert "プレースホルダ" in html                    # clearly labelled


def test_recorder_availability_reports_reason():
    ok, reason = CaptureRecorder().available()
    assert isinstance(ok, bool)
    if not ok:
        assert reason  # a human-readable reason is given


def test_capture_and_splice_into_video():
    recorder = CaptureRecorder()
    ok, _reason = recorder.available()
    if not ok:
        return  # environment lacks Playwright/Chromium/ffmpeg; skip gracefully

    cfg = load_config()
    pipeline = PlanPipeline(cfg)
    plan, out_dir = pipeline.run("Claude Code vs Codex", on_date=date(2026, 7, 21))
    pipeline.run_script_from_dir(out_dir)  # writes storyboard.json etc.

    manifest = pipeline.build_capture_from_dir(out_dir, created_at="2026-07-21T00:00:00")
    assert manifest.assets, "expected a recorded placeholder asset"
    asset = manifest.assets[0]
    assert not asset.is_real_service
    assert (out_dir / asset.video_path).exists()
    assert asset.duration > 0

    # The captured scene should now be spliced into the mp4.
    result = pipeline.build_video_from_dir(out_dir)
    assert result.ok, result.warnings
    assert (out_dir / result.path).exists()


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
