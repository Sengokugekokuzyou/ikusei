"""Fact QA (spec §13, §17: 公式確認なしの断定を禁止).

Every line marked as a factual claim must be backed by something in research or
the tool DB. Unsupported claims are flagged so a human (or a later real fact
checker) can catch "assertions without official confirmation".
"""

from __future__ import annotations

from ..schemas import FactQAReport, QAIssue, ResearchReport, Script


def _tokens(text: str) -> set[str]:
    # Coarse token set for JP/EN overlap (no morphological analyser in Phase 1).
    seps = "、。・（）()「」 　\n！？,."
    for ch in seps:
        text = text.replace(ch, " ")
    return {t for t in text.split() if len(t) >= 2}


class FactQA:
    def __init__(self, tool_db: dict, threshold: int = 95) -> None:
        self._tool_db = tool_db
        self._threshold = threshold

    def _support_corpus(self, script: Script, research: ResearchReport) -> list[str]:
        corpus: list[str] = [f.claim for f in research.findings]
        for name in script.comparison_targets or []:
            rec = self._tool_db.get(name, {})
            corpus.extend(rec.get("strengths", []))
            corpus.extend(rec.get("weaknesses", []))
            corpus.extend(rec.get("best_for", []))
            corpus.extend(rec.get("not_for", []))
            if rec.get("category"):
                corpus.append(rec["category"])
            p = rec.get("pricing", {})
            if p.get("free_tier") is False:
                corpus.append("無料枠がなく費用がかかる")
            if p.get("free_tier") is True:
                corpus.append("無料で試せる範囲がある")
            # "coding_agent" surfaces as コーディングエージェント in scripts.
            if rec.get("category") == "coding_agent":
                corpus.append("コーディングエージェント")
        return [c for c in corpus if c]

    def _supported(self, claim: str, corpus: list[str]) -> bool:
        for c in corpus:
            if c and (c in claim or claim in c):
                return True
        claim_tok = _tokens(claim)
        if not claim_tok:
            return False
        for c in corpus:
            overlap = claim_tok & _tokens(c)
            if len(overlap) >= 2:
                return True
        return False

    def _has_pricing_data(self, script: Script) -> bool:
        for name in script.comparison_targets or []:
            if self._tool_db.get(name, {}).get("pricing"):
                return True
        return False

    def run(self, script: Script, research: ResearchReport) -> FactQAReport:
        corpus = self._support_corpus(script, research)
        claims = [l for sec in script.sections for l in sec.lines if l.is_claim]
        pricing_words = ("無料", "費用", "料金", "有料", "プラン", "円")
        pricing_known = self._has_pricing_data(script)
        issues: list[QAIssue] = []
        supported = 0
        for line in claims:
            is_pricing = any(w in line.text for w in pricing_words)
            if self._supported(line.text, corpus) or (is_pricing and pricing_known):
                supported += 1
            else:
                issues.append(QAIssue("unsupported_claim", "fail",
                                      "根拠が確認できない断定", where=line.text[:40]))
        total = len(claims)
        score = round(supported / total * 100) if total else 100
        return FactQAReport(
            total_claims=total,
            supported_claims=supported,
            score=score,
            passed=score >= self._threshold,
            issues=issues,
        )
