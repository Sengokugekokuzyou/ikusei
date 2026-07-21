"""Thumbnail Judge (spec §64).

Rule-based scoring across the §63 visual rules (short text, <=3 subjects,
correct 1280×720 size, a hook). Picks the best of the >=3 candidates. Pure code,
so it needs no LLM and is deterministic.
"""

from __future__ import annotations

from ..schemas import ThumbnailCandidate


class ThumbnailJudge:
    def score(self, cand: ThumbnailCandidate) -> tuple[int, list[str]]:
        spec = cand.spec
        pts = 0
        notes: list[str] = []

        # Headline length: short is best (§63 "文字は2〜5語 / 小さい文字禁止").
        n = len(spec.text)
        if n <= 8:
            pts += 35
        elif n <= 12:
            pts += 25
            notes.append("見出しがやや長い")
        else:
            pts += 10
            notes.append("見出しが長すぎる(§63)")

        # Subjects: 1–3 is ideal; 0 or too many is worse (§63).
        ns = len(spec.subjects)
        if 1 <= ns <= 3:
            pts += 25
        elif ns == 0:
            pts += 10
            notes.append("主題が無い")
        else:
            pts += 10
            notes.append("主題が多すぎる(§63)")

        # A hook (question or VS) helps CTR without over-hype (§31).
        if "？" in spec.text or spec.text == "VS" or spec.layout == "split":
            pts += 20
        else:
            pts += 10

        # Correct resolution (§52: 1280×720).
        if (cand.width, cand.height) == (1280, 720):
            pts += 20
        else:
            notes.append(f"解像度が{cand.width}x{cand.height}(期待1280x720)")

        return min(pts, 100), notes

    def judge(self, candidates: list[ThumbnailCandidate]) -> str:
        best_label, best_score = "", -1
        for c in candidates:
            c.score, c.notes = self.score(c)
            if c.score > best_score:
                best_score, best_label = c.score, c.spec.label
        return best_label
