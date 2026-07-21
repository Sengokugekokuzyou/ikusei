"""Phase 3 tests. Runs under pytest, or standalone: `python tests/test_media.py`."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_navigator.config import load_config
from ai_navigator.pipeline import PlanPipeline
from ai_navigator.storyboard import to_srt, SubtitleBuilder
from ai_navigator.schemas import ResearchReport, SubtitleTrack, Subtitle
from ai_navigator.voice.base import estimate_duration


def _media():
    cfg = load_config()
    pipeline = PlanPipeline(cfg)
    plan, _ = pipeline.run("Claude Code vs Codex", on_date=date(2026, 7, 21))
    research = ResearchReport(topic=plan.topic, findings=[])
    script, _bqa, _fqa, tts = pipeline.build_script(plan, research)
    out_dir = Path(tempfile.mkdtemp(prefix="ainav-media-"))
    voice, storyboard, subtitles = pipeline.build_media(script, tts, out_dir)
    return script, tts, voice, storyboard, subtitles, out_dir


def test_estimate_duration_monotonic_and_speed():
    assert estimate_duration("あ" * 10) < estimate_duration("あ" * 30)
    assert estimate_duration("あ" * 20, speed=2.0) < estimate_duration("あ" * 20, speed=1.0)


def test_voice_manifest_timeline():
    _s, tts, voice, _sb, _subs, out_dir = _media()
    assert len(voice.clips) == len(tts.units)
    assert voice.total_duration > 0
    # Clips are laid out monotonically with no overlap.
    prev_end = 0.0
    for c in voice.clips:
        assert c.start >= prev_end - 1e-6
        assert c.end >= c.start
        prev_end = c.end + c.pause_after
    # Every clip has a real wav on disk.
    for c in voice.clips:
        assert (out_dir / c.audio_path).exists()


def test_storyboard_scenes_have_motion():
    _s, _tts, _voice, storyboard, _subs, _dir = _media()
    assert len(storyboard.scenes) > 0
    # §23: no scene is left fully static — each has a camera preset.
    for sc in storyboard.scenes:
        assert sc.camera and sc.camera != "static"
        assert sc.duration > 0


def test_storyboard_flags_low_real_capture():
    _s, _tts, _voice, storyboard, _subs, _dir = _media()
    # Mock has no real capture, so §22 warning must be present.
    assert any("実操作映像" in w for w in storyboard.warnings)
    assert storyboard.visual_mix.get("real_capture", 0.0) < 0.35


def test_comparison_scene_params():
    _s, _tts, _voice, storyboard, _subs, _dir = _media()
    comp = [s for s in storyboard.scenes if s.section == "comparison"]
    assert comp, "expected a comparison scene"
    assert comp[0].component == "VSComparison"
    assert comp[0].params.get("left") and comp[0].params.get("right")


def test_subtitles_align_to_voice():
    _s, _tts, voice, _sb, subtitles, _dir = _media()
    assert len(subtitles.subtitles) == len(voice.clips)
    for sub, clip in zip(subtitles.subtitles, voice.clips):
        assert abs(sub.start - clip.start) < 1e-6
        assert abs(sub.end - clip.end) < 1e-6


def test_resynth_voice_from_dir():
    # Full run to disk, then re-synthesize voice (mock) from the saved artifacts.
    cfg = load_config()
    pipeline = PlanPipeline(cfg)
    plan, out_dir = pipeline.run("Claude Code vs Codex", on_date=date(2026, 7, 21))
    pipeline.run_script_from_dir(out_dir)
    voice = pipeline.resynth_voice_from_dir(out_dir)
    assert len(voice.clips) > 0
    for name in ["voice", "storyboard", "subtitles"]:
        assert (out_dir / f"{name}.json").exists()
    assert (out_dir / "captions.srt").exists()


def test_srt_format():
    track = SubtitleTrack(topic="t", produced_at="d", subtitles=[
        Subtitle(index=1, start=0.0, end=1.5, text="こんにちは。"),
        Subtitle(index=2, start=1.85, end=3.0, text="AIの話です。"),
    ])
    srt = to_srt(track)
    assert "00:00:00,000 --> 00:00:01,500" in srt
    assert "00:00:01,850 --> 00:00:03,000" in srt
    assert "こんにちは。" in srt


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
