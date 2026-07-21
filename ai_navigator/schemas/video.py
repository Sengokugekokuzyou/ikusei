"""Video render result schema (spec §4-5 Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VideoResult:
    topic: str
    produced_at: str
    path: str = ""             # relative path to the rendered mp4
    width: int = 0
    height: int = 0
    fps: int = 30
    duration: float = 0.0
    scenes: int = 0
    has_audio: bool = False
    has_subtitles: bool = False
    motion: bool = False
    ok: bool = False
    warnings: list[str] = field(default_factory=list)
