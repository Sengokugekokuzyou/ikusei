"""Beginner Translator (spec §19).

A deterministic glossary that rewrites jargon into plain Japanese. Pure code (no
LLM needed) so it is fast, testable, and consistent across every video. Used to
flag/soften terms in titles and, later, scripts.
"""

from __future__ import annotations

import re

# term -> beginner-friendly explanation (spec §19 examples + common extras).
GLOSSARY: dict[str, str] = {
    "CLI": "文字でパソコンに指示を出す画面",
    "Repository": "プログラム一式が入った作業場所",
    "リポジトリ": "プログラム一式が入った作業場所",
    "Agent": "自分である程度考えながら作業を進めるAI",
    "エージェント": "自分である程度考えながら作業を進めるAI",
    "Token": "AIが文章を処理するための細かい単位",
    "トークン": "AIが文章を処理するための細かい単位",
    "API": "他のソフトからそのAIを呼び出すための窓口",
    "Terminal": "文字でパソコンを操作する黒い画面",
    "ターミナル": "文字でパソコンを操作する黒い画面",
    "デプロイ": "作ったものを実際に使える状態に公開すること",
    "プロンプト": "AIへの指示文",
}


class BeginnerTranslator:
    def __init__(self, glossary: dict[str, str] | None = None) -> None:
        self._glossary = glossary or GLOSSARY
        # Longest terms first so "Claude Code" style multiword wins over parts.
        self._terms = sorted(self._glossary, key=len, reverse=True)

    def find_terms(self, text: str) -> list[str]:
        """Return jargon terms present in the text (unique, order of appearance)."""
        found: list[str] = []
        for term in self._terms:
            if re.search(re.escape(term), text, flags=re.IGNORECASE):
                if term not in found:
                    found.append(term)
        return found

    def annotate(self, text: str) -> str:
        """Append a plain-language gloss the first time each term appears."""
        seen: set[str] = set()
        for term in self._terms:
            if term in seen:
                continue
            pattern = re.compile(re.escape(term), flags=re.IGNORECASE)

            def repl(m: re.Match, _term=term) -> str:
                if _term in seen:
                    return m.group(0)
                seen.add(_term)
                return f"{m.group(0)}（{self._glossary[_term]}）"

            text = pattern.sub(repl, text, count=1)
        return text
