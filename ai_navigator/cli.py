"""Command-line interface (spec §44).

    python -m ai_navigator plan --topic "Claude Code vs Codex"

Writes the six report artifacts and prints a short summary of the verdict.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
