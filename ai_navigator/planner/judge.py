"""Judge (spec §11, §43).

Maps each idea's total to a verdict, picks the winner, and decides whether to
produce at all. Core rule (spec §43): if nothing clears the bar, decline — the
system's purpose is quality, not volume.
"""

from __future__ import annotations

from ..schemas import (
    FactCheckReport,
    IdeaSet,
    ResearchReport,
    ScoreSet,
    SelectedPlan,
    Verdict,
)


class Judge:
    def __init__(self, video_min: int = 80, shorts_min: int = 65, min_fact_score: int = 95) -> None:
        self._video_min = video_min
        self._shorts_min = shorts_min
        self._min_fact_score = min_fact_score

    def _verdict(self, total: int) -> Verdict:
        if total >= self._video_min:
            return Verdict.VIDEO
        if total >= self._shorts_min:
            return Verdict.SHORTS
        return Verdict.DISCARD

    def run(
        self,
        topic: str,
        produced_at: str,
        idea_set: IdeaSet,
        score_set: ScoreSet,
        research: ResearchReport,
        fact: FactCheckReport,
    ) -> SelectedPlan:
        # Assign verdicts in place so scores.json reflects them.
        for s in score_set.scored:
            s.verdict = self._verdict(s.total)

        ranked = score_set.ranked()
        ideas_by_id = {i.id: i for i in idea_set.ideas}
        sources_used = [s.url for s in research.sources if s.url]

        if not ranked:
            return SelectedPlan(
                topic=topic,
                produced_at=produced_at,
                idea_id=-1,
                working_title="",
                produce=False,
                decline_reason="採点対象の企画がありません。",
                fact_score=fact.fact_score,
            )

        top = ranked[0]
        idea = ideas_by_id.get(top.idea_id)
        verdict = self._verdict(top.total)

        produce = True
        decline_reason = ""
        if verdict == Verdict.DISCARD:
            produce = False
            decline_reason = (
                f"最高スコアが{top.total}点で基準({self._shorts_min})未満。"
                "価値のあるテーマが無い日は動画を作らない(§43)。"
            )
        elif fact.fact_score < self._min_fact_score:
            produce = False
            decline_reason = (
                f"ファクトスコア{fact.fact_score}が基準{self._min_fact_score}未満。"
                "公式確認が取れるまで投稿しない(§13)。"
            )

        runner_up = ranked[1].total if len(ranked) > 1 else 0
        rationale = (
            f"{len(ranked)}案中で最高得点({top.total}点/{verdict.value})。"
            f"次点は{runner_up}点。{top.rationale}"
        )

        working_title = idea.title if idea else top.title
        title_candidates = self._seed_titles(idea, topic) if idea else [working_title]

        return SelectedPlan(
            topic=topic,
            produced_at=produced_at,
            idea_id=top.idea_id,
            working_title=working_title,
            title_candidates=title_candidates,
            rationale=rationale,
            target_viewer=idea.target_viewer if idea else "",
            comparison_targets=idea.comparison_targets if idea else [],
            sources_used=sources_used,
            score_total=top.total,
            verdict=verdict,
            fact_score=fact.fact_score,
            produce=produce,
            decline_reason=decline_reason,
        )

    @staticmethod
    def _seed_titles(idea, topic: str) -> list[str]:
        """A few title seeds for §31 to expand later (not the final 20)."""
        base = idea.title
        seeds = [base]
        if idea.comparison_targets and len(idea.comparison_targets) >= 2:
            a, b = idea.comparison_targets[0], idea.comparison_targets[1]
            seeds.append(f"{a}と{b}、結局どっち？初心者向けに解説")
            seeds.append(f"【{a} vs {b}】ChatGPTしか知らない人向け")
        else:
            seeds.append(f"{topic}って結局なに？初心者向けに解説")
            seeds.append(f"{topic}、どんな人が使うべき？")
        # De-dup preserving order.
        out: list[str] = []
        for s in seeds:
            if s not in out:
                out.append(s)
        return out
