"""Deterministic mock LLM provider.

Produces stable, plausible structured output for every pipeline stage without
any network call or API key. This is what makes "verify the whole structure
with no key" possible (the approach approved for Phase 1).

It is NOT a language model: it routes on the ``task`` hint and synthesises
output from the provided ``context`` (topic, tools, research, prior stage
output) using small rule-based templates. Good enough to exercise the pipeline
end to end and to eyeball the report shapes; real quality comes from wiring
``providers.text = "anthropic" | "openai"`` later.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .base import LLMProvider


def _stable_int(*parts: str, lo: int, hi: int) -> int:
    """Deterministic integer in [lo, hi] from string parts (no RNG)."""
    h = hashlib.sha256("::".join(parts).encode("utf-8")).hexdigest()
    span = hi - lo + 1
    return lo + (int(h[:8], 16) % span)


# Ten reusable idea angles (mirrors the spec §9 example set), templated on tools.
_IDEA_ANGLES = [
    ("新機能・概要まとめ", "{a}で結局なにができるようになったのかを一望する", "using"),
    ("{a} と {b} を初心者目線で比較", "{a}と{b}、名前は似てるけど何が違うのかを整理する", "compare"),
    ("初心者はまずどっち？", "AIに詳しくない人が最初に触るなら{a}と{b}のどちらか", "compare"),
    ("実際に同じ作業をさせてみた", "同じお題を{a}と{b}に渡して結果を並べて見せる", "demo"),
    ("{a} の使い方5つ", "{a}を今日から使うための具体的な使い方を5つ紹介する", "using"),
    ("無料の範囲だけでどこまで？", "{a}を無料の範囲だけで使うと何ができて何ができないか", "using"),
    ("{b} から {a} に乗り換えるべき？", "今{b}を使っている人が{a}に移る価値があるかを判定する", "compare"),
    ("結局どんな人に向いてる？", "{a}は結局どんな人が使うべきAIなのかを一言で言い切る", "using"),
    ("よくある誤解と注意点", "{a}について初心者が誤解しがちな点と気をつけることを解説", "using"),
    ("{a} と {b}、あなたはこっち", "タイプ別に{a}と{b}のどちらを使えばいいか振り分ける", "compare"),
]


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, tool_db: dict[str, Any] | None = None) -> None:
        # tool_db: {tool_name: AITool-as-dict}. Used as the mock's "knowledge".
        self._tool_db = tool_db or {}

    # complete() exists so the interface is honoured; real routing is in generate_json.
    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.7) -> str:
        return "[mock] " + prompt[:120]

    def generate_json(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.4,
        task: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        ctx = context or {}
        if task == "research":
            return self._research(ctx)
        if task == "fact_check":
            return self._fact_check(ctx)
        if task == "ideas":
            return self._ideas(ctx)
        if task == "critique":
            return self._critique(ctx)
        if task == "score":
            return self._score(ctx)
        raise ValueError(f"MockProvider has no route for task={task!r}")

    # --- helpers -----------------------------------------------------------
    def _tools(self, ctx: dict[str, Any]) -> list[str]:
        tools = ctx.get("tools") or []
        return [t for t in tools if t]

    def _tool_record(self, name: str) -> dict[str, Any]:
        return self._tool_db.get(name, {})

    # --- routes ------------------------------------------------------------
    def _research(self, ctx: dict[str, Any]) -> dict[str, Any]:
        topic = ctx.get("topic", "")
        tools = self._tools(ctx)
        sources: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        for t in tools:
            rec = self._tool_record(t)
            for url in rec.get("official_sources", []):
                sources.append(
                    {
                        "title": f"{t} official documentation",
                        "url": url,
                        "tier": 1,
                        "publisher": rec.get("category", ""),
                        "published_at": rec.get("updated_at", ""),
                        "usable_as_fact": True,
                    }
                )
            for s in rec.get("strengths", []):
                findings.append(
                    {
                        "claim": f"{t}は{s}",
                        "detail": "",
                        "source_urls": rec.get("official_sources", [])[:1],
                        "kind": "fact",
                    }
                )
        # A couple of Tier-4 "user pain" findings (reactions only, not facts).
        beginner_questions = [
            f"{tools[0]}と{tools[1]}って何が違うの？" if len(tools) >= 2 else f"{topic}って結局なに？",
            "自分にはどっちが向いてるのか分からない",
            "無料で使える？お金かかる？",
            "むずかしそうだけど初心者でも使える？",
        ]
        for q in beginner_questions[:2]:
            findings.append(
                {"claim": q, "detail": "初心者が抱える疑問", "source_urls": [], "kind": "user_pain"}
            )
        return {
            "tools_covered": tools,
            "sources": sources,
            "findings": findings,
            "beginner_questions": beginner_questions,
        }

    def _fact_check(self, ctx: dict[str, Any]) -> dict[str, Any]:
        tools = self._tools(ctx)
        items: list[dict[str, Any]] = []
        for t in tools:
            rec = self._tool_record(t)
            has_official = bool(rec.get("official_sources"))
            src = (rec.get("official_sources") or [""])[0]
            pricing = rec.get("pricing", {})
            free = pricing.get("free_tier")
            checks = {
                "pricing": ", ".join(pricing.get("paid_plans", [])) or "N/A",
                "free_plan": "yes" if free else ("no" if free is False else "unknown"),
                "api": "yes" if rec.get("category") else "unknown",
                "latest_version": rec.get("updated_at", "unknown"),
                "japanese_support": "unknown",
            }
            for fld, val in checks.items():
                items.append(
                    {
                        "field": fld,
                        "tool": t,
                        "value": val,
                        "verified": has_official,
                        "matches_official": has_official,
                        "source_url": src,
                        "note": "" if has_official else "no official source on record",
                    }
                )
        verified = [i for i in items if i["verified"]]
        fact_score = round(100 * len(verified) / len(items)) if items else 0
        notes = []
        if fact_score < 95:
            notes.append("一部の項目が公式ソースで未確認。実LLM/収集で要検証。")
        return {"items": items, "fact_score": fact_score, "notes": notes}

    def _ideas(self, ctx: dict[str, Any]) -> dict[str, Any]:
        topic = ctx.get("topic", "")
        tools = self._tools(ctx)
        a = tools[0] if tools else topic
        b = tools[1] if len(tools) >= 2 else "他のAI"
        n = int(ctx.get("n", 10))
        ideas = []
        for i, (title_t, angle_t, kind) in enumerate(_IDEA_ANGLES[:n], start=1):
            title = title_t.format(a=a, b=b)
            angle = angle_t.format(a=a, b=b)
            ideas.append(
                {
                    "id": i,
                    "title": title,
                    "angle": angle,
                    "description": f"{topic}について、{angle}。",
                    "target_viewer": "ChatGPTは知っているが選べないAI初心者",
                    "comparison_targets": [a, b] if kind == "compare" else [a],
                    "viewer_takeaway": (
                        f"{a}と{b}のどちらを使えばいいか分かる" if kind == "compare"
                        else f"{a}を実際に使い始められる"
                    ),
                }
            )
        return {"ideas": ideas}

    def _critique(self, ctx: dict[str, Any]) -> dict[str, Any]:
        idea = ctx.get("idea", {})
        title = idea.get("title", "")
        min_w = int(ctx.get("min", 5))
        is_compare = len(idea.get("comparison_targets", [])) >= 2
        pool = [
            "競合チャンネルが同種の比較を既に出しており差別化が要る",
            "初心者には固有名詞が多く、用語の言い換えが必須",
            "結論を一言で言い切れないと『用途による』オチになりやすい",
            "画面キャプチャが用意できないと動画映えが弱い",
            "情報が古くなりやすく公開時点の再確認が必要",
            "検索需要が一過性で長期再生されにくい可能性",
            "テンプレ的な構成だと量産AI動画に見えてしまう",
            "尺が長くなりがちで冒頭離脱のリスク",
        ]
        # Deterministically pick weaknesses, biasing compare-ideas slightly差別化.
        weaknesses = pool[: max(min_w, 5)]
        if not is_compare:
            weaknesses = weaknesses[:1] + ["比較構造がなく結論の切れ味を出しにくい"] + weaknesses[1:]
            weaknesses = weaknesses[: max(min_w, 5)]
        axis_notes = {
            "beginner_fit": "用語言い換えを入れれば初心者向けに成立",
            "conclusion_possible": "タイプ別の言い切りにできれば結論を出せる",
            "video_appeal": "実操作映像＋比較カードで映える",
        }
        return {"weaknesses": weaknesses, "axis_notes": axis_notes}

    def _score(self, ctx: dict[str, Any]) -> dict[str, Any]:
        idea = ctx.get("idea", {})
        title = idea.get("title", "")
        is_compare = len(idea.get("comparison_targets", [])) >= 2
        takeaway = idea.get("viewer_takeaway", "")
        has_conclusion = "どちら" in takeaway or "向いて" in takeaway or "使え" in takeaway
        seed = title

        # Heuristic per-axis scoring, biased toward the channel's core value:
        # beginner value + a clear conclusion + comparison need.
        beginner_value = _stable_int(seed, "bv", lo=17, hi=25)
        practicality = _stable_int(seed, "pr", lo=12, hi=20)
        search_demand = _stable_int(seed, "sd", lo=8, hi=15)
        topicality = _stable_int(seed, "to", lo=4, hi=10)
        comparison_need = (_stable_int(seed, "cn", lo=6, hi=10) if is_compare
                           else _stable_int(seed, "cn", lo=2, hi=6))
        video_appeal = _stable_int(seed, "va", lo=6, hi=10)
        differentiation = _stable_int(seed, "df", lo=2, hi=5)
        info_reliability = _stable_int(seed, "ir", lo=3, hi=5)
        if has_conclusion:
            beginner_value = min(25, beginner_value + 2)
        if is_compare:
            # Comparison content is the channel's differentiator: it maps to
            # higher 比較需要 / 動画映え(比較カード) / 差別化 (spec §22/§25/§2).
            video_appeal = min(10, video_appeal + 2)
            differentiation = min(5, differentiation + 1)
        breakdown = {
            "beginner_value": beginner_value,
            "practicality": practicality,
            "search_demand": search_demand,
            "topicality": topicality,
            "comparison_need": comparison_need,
            "video_appeal": video_appeal,
            "differentiation": differentiation,
            "info_reliability": info_reliability,
        }
        rationale = (
            "初心者価値と結論の明確さを重視。比較構造ありで比較需要を加点。"
            if is_compare
            else "単独解説のため比較需要は低め。実用性で評価。"
        )
        return {"breakdown": breakdown, "rationale": rationale}
