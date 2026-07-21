"""Data schemas for the AI Navigator pipeline.

Every artifact the pipeline writes to ``reports/`` has a dataclass here so the
JSON shape is defined in one place (spec §14, §12–13, §9, §10, §11, §44).

We use stdlib dataclasses (not pydantic) so Phase 1 runs with zero installs.
``dataclasses.asdict`` serialises nested dataclasses/lists recursively.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any


def to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass (or list/dict of them) to plain dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, list):
        return [to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj


def to_json(obj: Any, *, indent: int = 2) -> str:
    """Serialise a dataclass tree to pretty UTF-8 JSON (Japanese kept readable)."""
    return json.dumps(to_dict(obj), ensure_ascii=False, indent=indent)


from .tool import AITool, Pricing  # noqa: E402
from .research import (  # noqa: E402
    Source,
    SourceTier,
    Finding,
    FactCheckItem,
    FactCheckReport,
    ResearchReport,
)
from .idea import Idea, IdeaSet  # noqa: E402
from .critique import Critique, CritiqueSet  # noqa: E402
from .score import ScoreBreakdown, ScoredIdea, ScoreSet, Verdict  # noqa: E402
from .plan import SelectedPlan  # noqa: E402
from .script import (  # noqa: E402
    AudioUnit,
    Script,
    ScriptLine,
    ScriptSection,
    TTSScript,
    SECTION_ORDER,
    SECTION_LABELS,
)
from .qa import BeginnerQAReport, FactQAReport, QAIssue  # noqa: E402
from .storyboard import (  # noqa: E402
    VoiceClip,
    VoiceManifest,
    Scene,
    Storyboard,
    Subtitle,
    SubtitleTrack,
)
from .thumbnail import ThumbnailSpec, ThumbnailCandidate, ThumbnailSet  # noqa: E402

__all__ = [
    "to_dict",
    "to_json",
    "AITool",
    "Pricing",
    "Source",
    "SourceTier",
    "Finding",
    "FactCheckItem",
    "FactCheckReport",
    "ResearchReport",
    "Idea",
    "IdeaSet",
    "Critique",
    "CritiqueSet",
    "ScoreBreakdown",
    "ScoredIdea",
    "ScoreSet",
    "Verdict",
    "SelectedPlan",
    "Script",
    "ScriptLine",
    "ScriptSection",
    "AudioUnit",
    "TTSScript",
    "SECTION_ORDER",
    "SECTION_LABELS",
    "BeginnerQAReport",
    "FactQAReport",
    "QAIssue",
    "VoiceClip",
    "VoiceManifest",
    "Scene",
    "Storyboard",
    "Subtitle",
    "SubtitleTrack",
    "ThumbnailSpec",
    "ThumbnailCandidate",
    "ThumbnailSet",
]
