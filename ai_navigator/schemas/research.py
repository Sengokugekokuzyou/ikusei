"""Research + Fact-check schemas (spec §12, §13).

The Researcher gathers sources across a trust hierarchy (Tier 1 official ..
Tier 4 Reddit/X) and produces findings. The Fact Checker verifies the
concrete claims and records the video production date in metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class SourceTier(IntEnum):
    """Spec §12 trust hierarchy. Tier 4 is *reactions only*, never fact basis."""

    OFFICIAL = 1        # OpenAI / Anthropic / Google / Moonshot / GitHub / docs
    TECH_MEDIA = 2      # reputable tech media
    YOUTUBE = 3         # YouTube
    SOCIAL = 4          # Reddit / X — user reactions & pain points only


@dataclass
class Source:
    title: str
    url: str
    tier: SourceTier = SourceTier.OFFICIAL
    publisher: str = ""
    published_at: str = ""  # YYYY-MM-DD if known
    # Spec §12: Tier 4 is usable only as "user reaction", not as fact.
    usable_as_fact: bool = True

    def __post_init__(self) -> None:
        if self.tier == SourceTier.SOCIAL:
            self.usable_as_fact = False


@dataclass
class Finding:
    """A single claim/insight surfaced during research."""

    claim: str
    detail: str = ""
    source_urls: list[str] = field(default_factory=list)
    # "user_pain" findings capture what confuses/annoys real users (Tier 4).
    kind: str = "fact"  # "fact" | "user_pain" | "comparison" | "opinion"


@dataclass
class FactCheckItem:
    """One verifiable attribute (spec §13 checklist)."""

    field: str          # e.g. "pricing", "japanese_support", "api"
    tool: str
    value: str
    verified: bool = False
    matches_official: bool = False
    source_url: str = ""
    note: str = ""


@dataclass
class FactCheckReport:
    # Spec §13: record the production date in metadata.
    produced_at: str = ""  # YYYY-MM-DD the video/plan was produced
    items: list[FactCheckItem] = field(default_factory=list)
    # 0..100 confidence that facts are correct & official-consistent.
    fact_score: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass
class ResearchReport:
    topic: str
    produced_at: str = ""  # YYYY-MM-DD
    tools_covered: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    # Beginner pain points distilled from Tier 4 (spec §12, feeds §19 later).
    beginner_questions: list[str] = field(default_factory=list)
    fact_check: FactCheckReport = field(default_factory=FactCheckReport)
