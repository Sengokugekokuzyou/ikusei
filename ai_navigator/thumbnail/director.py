"""Thumbnail Director (spec §62, §64).

Produces at least 3 distinct candidate briefs per video. Follows §63 rules:
one big subject, <=2–3 tools, 2–5 short words, high contrast. Deliberately
avoids asserting a single "winner" in the image (the video gives the type-based
answer), so the thumbnail hooks without misleading (§31 no over-hype).
"""

from __future__ import annotations

from ..schemas import SelectedPlan, ThumbnailSpec

# Distinct high-contrast palettes so the 3 candidates look different (§64).
_PALETTES = [
    ("#0f172a", "#1e3a8a", "#f59e0b"),  # navy → blue, amber accent
    ("#111827", "#7c2d12", "#fbbf24"),  # dark → rust, gold accent
    ("#0b132b", "#3a0ca3", "#4cc9f0"),  # ink → purple, cyan accent
]


class ThumbnailDirector:
    def run(self, plan: SelectedPlan) -> list[ThumbnailSpec]:
        tools = plan.comparison_targets
        specs: list[ThumbnailSpec] = []
        p0, p1, p2 = _PALETTES

        if len(tools) >= 2:
            a, b = tools[0], tools[1]
            specs.append(ThumbnailSpec(
                label="A", text="結局どっち？", subjects=[a, b], layout="split",
                message="2つを比較して選び方を示す",
                bg_from=p0[0], bg_to=p0[1], accent=p0[2],
            ))
            specs.append(ThumbnailSpec(
                label="B", text="初心者はどっち？", subjects=[a, b], layout="question",
                message="初心者視点の選択を強調",
                bg_from=p1[0], bg_to=p1[1], accent=p1[2],
            ))
            specs.append(ThumbnailSpec(
                label="C", text="VS", subjects=[a, b], layout="split",
                message="ツール名を前面に出した対決構図",
                bg_from=p2[0], bg_to=p2[1], accent=p2[2],
            ))
        else:
            subj = tools[:1] or [plan.working_title]
            specs.append(ThumbnailSpec(
                label="A", text="結局なに？", subjects=subj, layout="question",
                message="正体を一言で問いかける",
                bg_from=p0[0], bg_to=p0[1], accent=p0[2],
            ))
            specs.append(ThumbnailSpec(
                label="B", text="誰が使うべき？", subjects=subj, layout="question",
                message="向いている人を問いかける",
                bg_from=p1[0], bg_to=p1[1], accent=p1[2],
            ))
            specs.append(ThumbnailSpec(
                label="C", text="初心者向け解説", subjects=subj, layout="recommend",
                message="初心者向けであることを明示",
                bg_from=p2[0], bg_to=p2[1], accent=p2[2],
            ))
        return specs
