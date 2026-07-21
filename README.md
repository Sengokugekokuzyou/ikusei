# AI Navigator

AIに詳しくない人向けに「増えすぎたAIを、調べて・試して・比較して "あなたはこれを使えばいい" と答える」YouTube動画を、可能な限り自動で制作・改善するためのシステムです。

このリポジトリは **Phase 1（Research + Planner）** の実装です。1つのトピックを入力すると、調査 → ファクトチェック → 企画10案 → ダメ出し → 採点 → 判定 までを自動で行い、人間がレビューできる形でレポートを出力します。

> 設計思想（仕様書 §43/§45）: 目的は動画の量産ではなく、初心者に本当に役立つ解説を高品質で作ること。**基準未満なら投稿しない。**

---

## クイックスタート

依存パッケージのインストールは不要です（Phase 1 は Python 3.11 標準ライブラリのみで動きます）。

```bash
python -m ai_navigator plan --topic "Claude Code vs Codex"
```

出力例:

```
✅ PRODUCE  (video)
Title     : Claude Code と Codex、あなたはこっち
Score     : 83/100   Fact: 100/100
Target    : ChatGPTは知っているが選べないAI初心者
Compare   : Claude Code vs Codex
```

レポートは `reports/YYYY-MM-DD_<slug>/` に6ファイル書き出されます（仕様 §44）:

| ファイル | 内容 |
|---|---|
| `research.json` | 調査結果（Tier1〜4のソース・findings・初心者の疑問） |
| `ideas.json` | 企画10案（§9） |
| `critique.json` | 各案の欠点 最低5個（§10） |
| `scores.json` | 100点満点の採点＋判定（§11） |
| `selected_plan.json` | 採用案・理由・タイトル候補・ターゲット・比較対象（§44） |
| `sources.json` | 使用ソース一覧 |

日付を固定したい場合: `--date 2026-07-21`。

---

## LLM プロバイダの設計

パイプラインの各工程は具体的なSDKではなく `LLMProvider` インターフェース1枚にだけ依存します。バックエンドは `config/default.toml` で切り替えます。

```toml
[providers]
text = "mock"      # "mock" | "anthropic" | "openai"
image = "openai"   # 後続フェーズ（画像生成 §46）用。Phase 1では未使用。
```

| プロバイダ | 役割 | キー |
|---|---|---|
| `mock` | **決定論的・APIキー不要**。ツールDBを知識源に構造化出力を合成。まず構造検証に使う | 不要 |
| `anthropic` | 推論・生成系（Researcher/企画/Critic/採点/台本…）に推奨 | `ANTHROPIC_API_KEY` |
| `openai` | テキスト、および将来の画像生成（§46） | `OPENAI_API_KEY` |

推奨構成は **テキスト=Claude / 画像=OpenAI のハイブリッド**。`text = "mock"` から実プロバイダへ切り替えても、工程コードは変更不要です。

キーは `.env` に置きます（`.env.example` をコピー）。`.env` は **絶対にコミットしない**（`.gitignore` 済み、仕様 §67）。

```bash
cp .env.example .env   # キーを記入
# config/default.toml の providers.text を "anthropic" などに変更
```

---

## アーキテクチャ

```
collector(将来) ─▶ research ─▶ fact-check ─▶ ideas(≥10) ─▶ critique ─▶ score ─▶ judge ─▶ reports/
```

```
ai_navigator/
├── cli.py / __main__.py     # python -m ai_navigator plan --topic ...
├── config.py                # TOML + .env 読み込み（stdlibのみ）
├── pipeline.py              # 各工程のオーケストレーション
├── schemas/                 # 全アーティファクトのdataclass定義
├── llm/                     # LLMProvider抽象 + mock/anthropic/openai
├── research/                # Researcher(§12) / FactChecker(§13) / BeginnerTranslator(§19)
├── planner/                 # IdeaGenerator(§9) / Critic(§10) / Scorer(§11) / Judge(§11)
└── database/                # AI Tool Database(§14)
config/default.toml          # 配点・閾値・プロバイダ設定
data/tools/*.json            # ツールDBのseed（mockの知識源）
reports/                     # 出力（gitignore）
tests/                       # Phase 1 テスト
```

### 採点と判定（§11）

100点満点・8軸。配点は `config/default.toml` の `[planner.score_weights]`（合計100）。

| 合計点 | 判定 |
|---|---|
| 80以上 | 通常動画候補 |
| 65〜79 | Shorts候補 |
| 64以下 | 廃棄 |

さらに Judge は、最高スコアが基準未満、またはファクトスコアが `fact_check.min_fact_score`（既定95）未満なら、**その日は作らない**判断を返します（§13/§43）。

---

## テスト

```bash
python tests/test_planning.py     # pytestなしで実行可能
# または pytest を入れて: pytest -q
```

---

## ロードマップ

- **Phase 1（本実装）**: Research + Planner ✅
- Phase 2: Script System（初心者向け台本 / TTS整形 / Beginner QA）
- Phase 3: Voice + Storyboard（VOICEVOX / 字幕タイムコード / Scene分割）
- Phase 4: 動画生成（Remotion / FFmpeg）
- Phase 5: Browser Capture（Playwright 実操作録画）
- Phase 6: Video QA / Phase 7: YouTube / Phase 8: Analytics

詳細は仕様書 §39 を参照。

---

## 注意

`data/tools/*.json` の内容は現状 **seed のプレースホルダ** です。実際の料金・仕様は公開前に公式ソースで再確認してください（仕様 §12/§13）。
