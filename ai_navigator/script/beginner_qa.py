"""Beginner QA (spec §20) — rule-based, so it gives real signal under any LLM.

Scores the script 0–100 across the §20 checklist. Below the threshold (80) the
pipeline regenerates. Checks intentionally avoid an LLM judge here: they are
deterministic and cheap, which is what a gate wants.
"""

from __future__ import annotations

from ..research import BeginnerTranslator
from ..schemas import BeginnerQAReport, QAIssue, Script
from .tts_formatter import split_sentences

# Forbidden non-conclusions (spec §18).
_FORBIDDEN_CONCLUSIONS = ["用途によ", "どれも良い", "どちらも良い", "好みで", "人それぞれ"]

# check_key -> weight (sums to 100).
_WEIGHTS = {
    "terms_explained": 20,
    "sentence_length": 20,
    "has_examples": 15,
    "has_pricing": 15,
    "has_next_action": 10,
    "clear_conclusion": 20,
}

_MAX_SENTENCE_CHARS = 60


class BeginnerQA:
    def __init__(self, threshold: int = 80, translator: BeginnerTranslator | None = None) -> None:
        self._threshold = threshold
        self._translator = translator or BeginnerTranslator()

    def run(self, script: Script, attempts: int = 1) -> BeginnerQAReport:
        text = script.full_text()
        issues: list[QAIssue] = []
        checks: dict[str, int] = {}

        # 1) Jargon must be explained (glossary gloss present, or no jargon at all).
        terms = self._translator.find_terms(text)
        if not terms:
            checks["terms_explained"] = 100
        else:
            explained = sum(1 for t in terms if self._translator._glossary[t] in text)
            frac = explained / len(terms)
            checks["terms_explained"] = round(frac * 100)
            for t in terms:
                if self._translator._glossary[t] not in text:
                    issues.append(QAIssue("terms_explained", "fail",
                                          f"専門用語『{t}』の説明がありません", where=t))

        # 2) Sentence length.
        sentences = [s for line in (l for sec in script.sections for l in sec.lines)
                     for s in split_sentences(line.text)]
        if sentences:
            ok = sum(1 for s in sentences if len(s) <= _MAX_SENTENCE_CHARS)
            checks["sentence_length"] = round(ok / len(sentences) * 100)
            for s in sentences:
                if len(s) > _MAX_SENTENCE_CHARS:
                    issues.append(QAIssue("sentence_too_long", "warn",
                                          f"1文が長い({len(s)}字)", where=s[:30] + "…"))
        else:
            checks["sentence_length"] = 0

        # 3) Concrete examples (bullets or 例/たとえば).
        has_examples = ("・" in text) or ("たとえば" in text) or ("例えば" in text)
        checks["has_examples"] = 100 if has_examples else 0
        if not has_examples:
            issues.append(QAIssue("has_examples", "warn", "具体例が見当たりません"))

        # 4) Pricing explained.
        has_pricing = any(w in text for w in ["料金", "無料", "費用", "円", "プラン", "有料"])
        checks["has_pricing"] = 100 if has_pricing else 0
        if not has_pricing:
            issues.append(QAIssue("has_pricing", "warn", "料金の説明がありません"))

        # 5) Next action ("使い始め方が分かるか").
        has_next = any(w in text for w in ["まず", "次に", "開いて", "触って", "試して", "登録"])
        checks["has_next_action"] = 100 if has_next else 0
        if not has_next:
            issues.append(QAIssue("has_next_action", "warn", "次にやることが不明"))

        # 6) Clear conclusion (final_decision present, non-empty, not a hedge).
        final = script.section("final_decision")
        final_text = " ".join(l.text for l in final.lines) if final else ""
        hedged = any(bad in final_text for bad in _FORBIDDEN_CONCLUSIONS)
        if final_text and not hedged:
            checks["clear_conclusion"] = 100
        else:
            checks["clear_conclusion"] = 0
            issues.append(QAIssue("clear_conclusion", "fail",
                                  "結論が無い/濁している(§18)", where=final_text[:40]))

        score = round(sum(checks[k] * w for k, w in _WEIGHTS.items()) / 100)
        return BeginnerQAReport(
            checks=checks,
            score=score,
            passed=score >= self._threshold,
            issues=issues,
            attempts=attempts,
        )
