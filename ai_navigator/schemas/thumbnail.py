"""Thumbnail schemas (spec §61-64).

Thumbnails are composed in HTML/CSS and rendered to PNG by headless Chromium —
a free, key-less path that also matches §54 (text is added in composition, not
baked into a generated image), so Japanese never mis-renders.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ThumbnailSpec:
    """Design brief for one candidate (spec §62)."""

    label: str                 # "A" | "B" | "C"
    text: str                  # headline, 2–5 words / short (§63)
    subjects: list[str] = field(default_factory=list)  # tool names (<=3, §63)
    layout: str = "question"   # "split" | "question" | "recommend"
    message: str = ""          # what the thumbnail communicates
    emotion: str = "confusion to clarity"
    target: str = "AI初心者"
    # Palette (kept high-contrast, §63). Filled by the director.
    bg_from: str = "#0f172a"
    bg_to: str = "#1e3a8a"
    accent: str = "#f59e0b"


@dataclass
class ThumbnailCandidate:
    spec: ThumbnailSpec
    image_path: str = ""       # relative path to the rendered PNG
    width: int = 0
    height: int = 0
    score: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass
class ThumbnailSet:
    topic: str
    produced_at: str
    renderer: str = "chromium"
    chosen_label: str = ""
    candidates: list[ThumbnailCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
