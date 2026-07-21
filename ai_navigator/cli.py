"""Command-line interface (spec §44).

    python -m ai_navigator plan --topic "Claude Code vs Codex"

Writes the six report artifacts and prints a short summary of the verdict.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .config import load_config
from .pipeline import PlanPipeline
from .schemas import Verdict


def _cmd_plan(args: argparse.Namespace) -> int:
    cfg = load_config()
    on_date = date.fromisoformat(args.date) if args.date else None
    pipeline = PlanPipeline(cfg)
    plan, out_dir = pipeline.run(args.topic, on_date=on_date)

    provider = cfg.get("providers.text", "mock")
    print(f"Topic     : {plan.topic}")
    print(f"Provider  : {provider}")
    print(f"Output    : {out_dir}")
    print("-" * 48)
    if plan.produce:
        print(f"✅ PRODUCE  ({plan.verdict.value})")
        print(f"Title     : {plan.working_title}")
        print(f"Score     : {plan.score_total}/100   Fact: {plan.fact_score}/100")
        print(f"Target    : {plan.target_viewer}")
        if plan.comparison_targets:
            print(f"Compare   : {' vs '.join(plan.comparison_targets)}")
        print(f"Why       : {plan.rationale}")
        print("Titles    :")
        for t in plan.title_candidates:
            print(f"  - {t}")
    else:
        print("🛑 DECLINE — 今日は投稿しない")
        print(f"Reason    : {plan.decline_reason}")
    return 0


def _print_thumbnail_result(thumbs) -> None:
    print("-" * 48)
    if thumbs.warnings:
        for w in thumbs.warnings:
            print(f"🖼️  ⚠️  {w}")
        return
    print(f"🖼️  Thumbnails : {len(thumbs.candidates)} candidates (chosen: {thumbs.chosen_label})")
    for c in thumbs.candidates:
        mark = "★" if c.spec.label == thumbs.chosen_label else " "
        note = f" — {', '.join(c.notes)}" if c.notes else ""
        print(f"  {mark} {c.spec.label}: 「{c.spec.text}」 {c.width}x{c.height} score={c.score}{note}")


def _print_script_result(bqa, fqa, storyboard, out_dir: Path) -> None:
    print("-" * 48)
    b = "✅" if bqa.passed else "🛑"
    f = "✅" if fqa.passed else "🛑"
    print(f"{b} Beginner QA : {bqa.score}/100 (pass>=80, attempts={bqa.attempts})")
    print(f"{f} Fact QA     : {fqa.score}/100 ({fqa.supported_claims}/{fqa.total_claims} claims, pass>=95)")
    if bqa.issues or fqa.issues:
        print("Issues:")
        for iss in (bqa.issues + fqa.issues):
            print(f"  [{iss.severity}] {iss.check}: {iss.detail}")
    print("-" * 48)
    mm = int(storyboard.total_duration // 60)
    ss = int(storyboard.total_duration % 60)
    print(f"🎬 Storyboard : {len(storyboard.scenes)} scenes, 尺 {mm}:{ss:02d}")
    mix = ", ".join(f"{k} {v:.0%}" for k, v in sorted(storyboard.visual_mix.items()))
    print(f"Visual mix  : {mix}")
    for w in storyboard.warnings:
        print(f"  ⚠️  {w}")
    print(f"Artifacts   : {out_dir}/ (script/storyboard/subtitles.json, captions.srt, voice/*.wav)")


def _cmd_script(args: argparse.Namespace) -> int:
    cfg = load_config()
    report_dir = Path(args.plan)
    if not (report_dir / "selected_plan.json").exists():
        print(f"error: {report_dir}/selected_plan.json not found. Run `plan` first.", file=sys.stderr)
        return 2
    pipeline = PlanPipeline(cfg)
    _script, bqa, fqa, storyboard, thumbs = pipeline.run_script_from_dir(report_dir)
    print(f"Report dir : {report_dir}")
    _print_script_result(bqa, fqa, storyboard, report_dir)
    _print_thumbnail_result(thumbs)
    return 0


def _print_video_result(video, out_dir: Path) -> None:
    print("-" * 48)
    if not video.ok:
        for w in video.warnings:
            print(f"🎞️  ⚠️  {w}")
        return
    flags = []
    if video.has_audio:
        flags.append("音声")
    if video.has_subtitles:
        flags.append("字幕")
    if video.motion:
        flags.append("モーション")
    mm, ss = int(video.duration // 60), int(video.duration % 60)
    print(f"🎞️  Video      : {video.path}  {video.width}x{video.height}@{video.fps}fps  "
          f"{mm}:{ss:02d}  [{'/'.join(flags)}]")
    print(f"             {out_dir}/{video.path}")


def _cmd_speakers(args: argparse.Namespace) -> int:
    """List VOICEVOX speakers/styles from a running engine (to pick an id)."""
    import json
    import urllib.request
    cfg = load_config()
    endpoint = args.endpoint or cfg.get("voice.endpoint", "http://127.0.0.1:50021")
    url = endpoint.rstrip("/") + "/speakers"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            speakers = json.loads(resp.read())
    except Exception as exc:
        print(f"VOICEVOXエンジンに接続できません（{endpoint}）: {exc}", file=sys.stderr)
        print("エンジン起動: docker run --rm -p 50021:50021 "
              "voicevox/voicevox_engine:cpu-ubuntu20.04-latest", file=sys.stderr)
        return 1
    for sp in speakers:
        name = sp.get("name", "")
        for st in sp.get("styles", []):
            print(f"  {st.get('id'):>4}  {name} / {st.get('name','')}")
    return 0


def _cmd_voice(args: argparse.Namespace) -> int:
    cfg = load_config()
    # CLI overrides so no config edit is needed for a local VOICEVOX run.
    if getattr(args, "adapter", None):
        cfg.set("voice.adapter", args.adapter)
    if getattr(args, "endpoint", None):
        cfg.set("voice.endpoint", args.endpoint)
    if getattr(args, "speaker", None) is not None:
        cfg.set("voice.speaker", args.speaker)
    report_dir = Path(args.plan)
    if not (report_dir / "script_tts.json").exists():
        print(f"error: {report_dir}/script_tts.json not found. Run `script` first.", file=sys.stderr)
        return 2
    adapter = cfg.get("voice.adapter", "mock")
    pipeline = PlanPipeline(cfg)
    try:
        voice = pipeline.resynth_voice_from_dir(report_dir)
    except Exception as exc:  # e.g. VoicevoxUnavailable
        print(f"🔊 音声合成に失敗しました（adapter={adapter}）:\n   {exc}", file=sys.stderr)
        return 1
    mm, ss = int(voice.total_duration // 60), int(voice.total_duration % 60)
    silent = adapter == "mock"
    print(f"🔊 Voice re-synth : adapter={adapter}  clips={len(voice.clips)}  尺 {mm}:{ss:02d}"
          + ("  (mockは無音)" if silent else ""))
    print(f"             {report_dir}/voice/  (+ storyboard/subtitles を再タイミング)")
    if silent:
        print("   実音声にするには config の voice.adapter を \"voicevox\" にし、"
              "エンジン起動後に再実行してください。")
    return 0


def _cmd_capture(args: argparse.Namespace) -> int:
    from datetime import datetime
    cfg = load_config()
    report_dir = Path(args.plan)
    if not (report_dir / "storyboard.json").exists():
        print(f"error: {report_dir}/storyboard.json not found. Run `script` first.", file=sys.stderr)
        return 2
    pipeline = PlanPipeline(cfg)
    created = datetime.now().isoformat(timespec="seconds")
    manifest = pipeline.build_capture_from_dir(report_dir, created)
    print(f"Report dir : {report_dir}")
    print("-" * 48)
    if manifest.assets:
        for a in manifest.assets:
            tag = "実サービス" if a.is_real_service else "プレースホルダ"
            print(f"🎥 Capture    : {a.video_path}  {a.duration:.1f}s  scene#{a.scene_id}  [{tag}]")
    else:
        print("🎥 Capture    : （収録なし）")
    for w in manifest.warnings:
        print(f"   ⚠️  {w}")
    print("   → `video --plan` で該当シーンに実映像が合成されます。")
    return 0


def _cmd_video(args: argparse.Namespace) -> int:
    cfg = load_config()
    report_dir = Path(args.plan)
    if not (report_dir / "storyboard.json").exists():
        print(f"error: {report_dir}/storyboard.json not found. Run `script` first.", file=sys.stderr)
        return 2
    pipeline = PlanPipeline(cfg)
    video = pipeline.build_video_from_dir(report_dir)
    print(f"Report dir : {report_dir}")
    _print_video_result(video, report_dir)
    return 0 if video.ok else 1


def _open_file(path: Path) -> None:
    import os
    import subprocess
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass  # opening is a convenience; never fail the run over it


def _cmd_run(args: argparse.Namespace) -> int:
    """plan -> (if produce) script, and optionally VOICEVOX audio + video."""
    cfg = load_config()
    # Real VOICEVOX narration for the whole run (validated up front).
    if getattr(args, "voicevox", False):
        cfg.set("voice.adapter", "voicevox")
        if args.endpoint:
            cfg.set("voice.endpoint", args.endpoint)
        if args.speaker is not None:
            cfg.set("voice.speaker", args.speaker)
        try:
            from .voice import build_adapter
            build_adapter("voicevox", endpoint=cfg.get("voice.endpoint", ""),
                          speaker=cfg.get("voice.speaker", 3))  # pings /version
            print("🔊 VOICEVOX 接続OK — 実音声で生成します。")
        except Exception as exc:
            print(f"🔊 ⚠️  VOICEVOXに接続できず、無音(mock)で続行します:\n   {exc}", file=sys.stderr)
            cfg.set("voice.adapter", "mock")

    on_date = date.fromisoformat(args.date) if args.date else None
    pipeline = PlanPipeline(cfg)
    plan, out_dir = pipeline.run(args.topic, on_date=on_date)
    _cmd_plan_print(plan, out_dir, cfg)
    if not plan.produce:
        return 0
    _script, bqa, fqa, storyboard, thumbs = pipeline.run_script_from_dir(out_dir)
    _print_script_result(bqa, fqa, storyboard, out_dir)
    _print_thumbnail_result(thumbs)
    if getattr(args, "video", False):
        video = pipeline.build_video_from_dir(out_dir)
        _print_video_result(video, out_dir)
        if getattr(args, "open", False) and video.ok:
            _open_file(out_dir / video.path)
    return 0


def _cmd_plan_print(plan, out_dir, cfg) -> None:
    provider = cfg.get("providers.text", "mock")
    print(f"Topic     : {plan.topic}")
    print(f"Provider  : {provider}")
    print(f"Output    : {out_dir}")
    print("-" * 48)
    if plan.produce:
        print(f"✅ PRODUCE  ({plan.verdict.value})")
        print(f"Title     : {plan.working_title}")
        print(f"Score     : {plan.score_total}/100   Fact: {plan.fact_score}/100")
        if plan.comparison_targets:
            print(f"Compare   : {' vs '.join(plan.comparison_targets)}")
    else:
        print("🛑 DECLINE — 今日は投稿しない")
        print(f"Reason    : {plan.decline_reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_navigator",
        description="AI Navigator — beginner-friendly AI explainer video planner (Phase 1)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Research + plan a video for a topic")
    plan.add_argument("--topic", required=True, help='e.g. "Claude Code vs Codex"')
    plan.add_argument("--date", default=None, help="Override production date (YYYY-MM-DD)")
    plan.set_defaults(func=_cmd_plan)

    script = sub.add_parser("script", help="Write + QA a script from an existing plan dir")
    script.add_argument("--plan", required=True, help="reports/YYYY-MM-DD_<slug>/ directory")
    script.set_defaults(func=_cmd_script)

    run = sub.add_parser("run", help="plan -> script (+ --voicevox / --video), end to end")
    run.add_argument("--topic", required=True, help='e.g. "Claude Code vs Codex"')
    run.add_argument("--date", default=None, help="Override production date (YYYY-MM-DD)")
    run.add_argument("--video", action="store_true", help="Also render the mp4 (Phase 4)")
    run.add_argument("--voicevox", action="store_true", help="Use a running VOICEVOX engine for real audio")
    run.add_argument("--speaker", type=int, default=None, help="VOICEVOX speaker/style id (with --voicevox)")
    run.add_argument("--endpoint", default=None, help="VOICEVOX endpoint URL (with --voicevox)")
    run.add_argument("--open", action="store_true", help="Open the finished mp4 when done")
    run.set_defaults(func=_cmd_run)

    voice = sub.add_parser("voice", help="(Re)synthesize narration for a dir with the configured adapter")
    voice.add_argument("--plan", required=True, help="reports/YYYY-MM-DD_<slug>/ directory")
    voice.add_argument("--adapter", default=None, choices=["mock", "voicevox"],
                       help="Override voice.adapter (e.g. voicevox)")
    voice.add_argument("--endpoint", default=None, help="Override VOICEVOX endpoint URL")
    voice.add_argument("--speaker", type=int, default=None, help="Override VOICEVOX speaker/style id")
    voice.set_defaults(func=_cmd_voice)

    speakers = sub.add_parser("speakers", help="List VOICEVOX speakers/styles from a running engine")
    speakers.add_argument("--endpoint", default=None, help="VOICEVOX endpoint URL (default from config)")
    speakers.set_defaults(func=_cmd_speakers)

    capture = sub.add_parser("capture", help="Record demo operation footage (Playwright) for a dir")
    capture.add_argument("--plan", required=True, help="reports/YYYY-MM-DD_<slug>/ directory")
    capture.set_defaults(func=_cmd_capture)

    video = sub.add_parser("video", help="Render the mp4 from an existing script/storyboard dir")
    video.add_argument("--plan", required=True, help="reports/YYYY-MM-DD_<slug>/ directory")
    video.set_defaults(func=_cmd_video)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
