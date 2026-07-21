"""QA schemas (spec §20 Beginner QA, §13/§17 Fact QA).

Both QA stages are rule-based (pure code) so they give real signal regardless
of which LLM backend wrote the script.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QAIssue:
    check: str        # machine key, e.g. "sentence_too_long"
    severity: str = "warn"  # "warn" | "fail"
    detail: str = ""
    where: str = ""   # section or line excerpt


@dataclass
class BeginnerQAReport:
    # Per-check 0..100 sub-scores (keys are the §20 checklist items).
    checks: dict[str, int] = field(default_factory=dict)
    score: int = 0
    passed: bool = False        # score >= threshold (default 80)
    issues: list[QAIssue] = field(default_factory=list)
    attempts: int = 1           # how many writer attempts it took


@dataclass
class FactQAReport:
    total_claims: int = 0
    supported_claims: int = 0
    score: int = 0              # supported / total * 100
    passed: bool = False        # score >= threshold (default 95, spec §30)
    issues: list[QAIssue] = field(default_factory=list)
