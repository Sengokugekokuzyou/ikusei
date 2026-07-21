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


def _cmd_voice(args: argparse.Namespace) -> int:
    cfg = load_config()
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


def _cmd_run(args: argparse.Namespace) -> int:
    """plan -> (if produce) script, and optionally video, end to end."""
    cfg = load_config()
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

    run = sub.add_parser("run", help="plan -> script (+ --video), end to end")
    run.add_argument("--topic", required=True, help='e.g. "Claude Code vs Codex"')
    run.add_argument("--date", default=None, help="Override production date (YYYY-MM-DD)")
    run.add_argument("--video", action="store_true", help="Also render the mp4 (Phase 4)")
    run.set_defaults(func=_cmd_run)

    voice = sub.add_parser("voice", help="(Re)synthesize narration for a dir with the configured adapter")
    voice.add_argument("--plan", required=True, help="reports/YYYY-MM-DD_<slug>/ directory")
    voice.set_defaults(func=_cmd_voice)

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
