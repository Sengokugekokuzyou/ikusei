"""Phase 4 (video) tests. Standalone: `python tests/test_video.py`.

Heavy render steps are guarded on ffmpeg/Chromium availability so the suite
still passes on machines without them.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_navigator.config import load_config
from ai_navigator.htmlrender import find_chrome
from ai_navigator.pipeline import PlanPipeline
from ai_navigator.storyboard.subtitles import wrap_jp
from ai_navigator.video import VideoBuilder, ffmpeg_has_full_support, find_ffmpeg
from ai_navigator.video.audio import build_narration_wav
from ai_navigator.video.builder import _kenburns_vf
from ai_navigator.video.frames import build_scene_html
from ai_navigator.schemas import ResearchReport, Scene


def _media(tmp: Path):
    cfg = load_config()
    pipeline = PlanPipeline(cfg)
    plan, _ = pipeline.run("Claude Code vs Codex", on_date=date(2026, 7, 21))
    research = ResearchReport(topic=plan.topic, findings=[])
    script, _b, _f, tts = pipeline.build_script(plan, research)
    voice, storyboard, subtitles = pipeline.build_media(script, tts, tmp)
    return cfg, pipeline, plan, script, voice, storyboard, subtitles


def test_wrap_jp():
    assert wrap_jp("短い") == "短い"
    wrapped = wrap_jp("あ" * 45, max_chars=20)
    assert "\n" in wrapped
    assert all(len(line) <= 20 for line in wrapped.split("\n"))


def test_kenburns_vf_varies_and_sets_frames():
    a = _kenburns_vf(0, 5.0, 30)
    b = _kenburns_vf(1, 5.0, 30)
    c = _kenburns_vf(2, 5.0, 30)
    assert "d=150" in a and "zoompan" in a
    assert a != b != c  # three distinct motions
    assert "crop=1280:720:0:0" in a  # takes the top region of the tall frame


def test_scene_html_has_chip_and_content():
    sc = Scene(scene_id=1, section="comparison", duration=4.0, voice="比較です。",
               visual_type="comparison_card", component="VSComparison",
               params={"left": "Claude Code", "right": "Codex", "highlight": "left"})
    html = build_scene_html(sc, "タイトル")
    assert "Claude Code" in html and "Codex" in html and "VS" in html
    assert "IPAGothic" in html


def test_narration_wav_matches_timeline():
    tmp = Path(tempfile.mkdtemp(prefix="ainav-vid-"))
    _cfg, _p, _plan, _script, voice, _sb, _subs = _media(tmp)
    dur = build_narration_wav(voice, tmp, tmp / "narration.wav")
    assert (tmp / "narration.wav").exists()
    # Narration length should be close to the storyboard/voice timeline.
    assert abs(dur - voice.total_duration) < 1.0


def test_ffmpeg_available_is_full_if_present():
    ff = find_ffmpeg()
    if ff:
        # imageio-ffmpeg (installed in this env) is a full build.
        assert ffmpeg_has_full_support(ff)


def test_video_build_smoke():
    if not (find_ffmpeg() and find_chrome()):
        return  # environment lacks tools; skip gracefully
    ff = find_ffmpeg()
    if not ffmpeg_has_full_support(ff):
        return
    tmp = Path(tempfile.mkdtemp(prefix="ainav-vidbuild-"))
    cfg, _p, _plan, _script, voice, storyboard, subtitles = _media(tmp)
    # Trim to 2 scenes to keep the render fast.
    storyboard.scenes = storyboard.scenes[:2]
    from ai_navigator.storyboard import to_srt
    (tmp / "captions.srt").write_text(to_srt(subtitles), encoding="utf-8")
    result = VideoBuilder(cfg).run(storyboard, voice, tmp)
    assert result.ok, result.warnings
    assert (tmp / result.path).exists()
    assert (result.width, result.height) == (1280, 720)
    assert result.has_audio and result.has_subtitles


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
