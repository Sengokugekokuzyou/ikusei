"""Voice + Storyboard + Subtitle schemas (spec §7/§8, §21-24, §28).

Phase 3 turns the TTS units into timed narration clips, then derives a scene
storyboard (visual instructions) and a subtitle track from that timing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VoiceClip:
    """One synthesised narration unit with its place on the timeline."""

    id: int
    section: str
    line: int          # global script-line index this clip belongs to
    text: str
    start: float       # seconds from video start (speech begins)
    end: float         # speech ends
    duration: float    # speech length
    pause_after: float # gap before the next clip
    audio_path: str = ""  # relative path to the wav (may be a silent placeholder)


@dataclass
class VoiceManifest:
    topic: str
    produced_at: str
    adapter: str = "mock"
    total_duration: float = 0.0
    clips: list[VoiceClip] = field(default_factory=list)


@dataclass
class Scene:
    """A single storyboard scene (spec §21)."""

    scene_id: int
    section: str
    duration: float
    voice: str
    visual_type: str           # real_capture | motion_graphic | comparison_card | broll | static
    component: str = ""        # Remotion component (§25), e.g. "VSComparison"
    params: dict = field(default_factory=dict)  # left/right/items/price…
    animation: str = "fade_in"
    camera: str = "slow_push"  # §60 motion preset — never fully static (§23)
    start: float = 0.0


@dataclass
class Storyboard:
    topic: str
    produced_at: str
    working_title: str
    total_duration: float = 0.0
    scenes: list[Scene] = field(default_factory=list)
    # §22 visual-ratio self-report {visual_type: fraction}.
    visual_mix: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Subtitle:
    index: int
    start: float
    end: float
    text: str
    emphasis: list[str] = field(default_factory=list)


@dataclass
class SubtitleTrack:
    topic: str
    produced_at: str
    subtitles: list[Subtitle] = field(default_factory=list)
