"""AI Tool Database schema (spec §14).

Each AI product the channel covers gets one record capturing its latest known
state, used by the Researcher and Planner to reason about comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Pricing:
    """Loosely structured pricing so we can hold whatever a tool publishes."""

    free_tier: bool | None = None
    paid_plans: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class AITool:
    tool: str
    category: str = ""  # e.g. "coding_agent", "chat_assistant"
    updated_at: str = ""  # YYYY-MM-DD, when this record was last verified
    pricing: Pricing = field(default_factory=Pricing)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    best_for: list[str] = field(default_factory=list)
    not_for: list[str] = field(default_factory=list)
    official_sources: list[str] = field(default_factory=list)
