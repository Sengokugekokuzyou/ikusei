"""Planner idea schema (spec §9).

Per topic the generator produces >= 10 distinct video ideas. Each idea is an
angle on the topic, aimed at the beginner audience, with a concrete decision
the video will help the viewer make.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Idea:
    id: int
    title: str                 # working title (final titles come later, §31)
    angle: str                 # the hook / framing in one line
    description: str = ""       # what the video covers
    target_viewer: str = ""     # who this is for (§1-1)
    comparison_targets: list[str] = field(default_factory=list)
    # The concrete question the viewer can answer after watching (§1-2).
    viewer_takeaway: str = ""


@dataclass
class IdeaSet:
    topic: str
    ideas: list[Idea] = field(default_factory=list)
