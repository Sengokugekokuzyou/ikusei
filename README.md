# AI Navigator

AIに詳しくない人向けに「増えすぎたAIを、調べて・試して・比較して "あなたはこれを使えばいい" と答える」YouTube動画を、可能な限り自動で制作・改善するためのシステムです。

このリポジトリは **Phase 1（Research + Planner）＋ Phase 2（Script System）** の実装です。1つのトピックを入力すると、調査 → ファクトチェック → 企画10案 → ダメ出し → 採点 → 判定 → 台本 → TTS整形 → 初心者QA → ファクトQA までを自動で行い、人間がレビューできる形でレポートを出力します。

> 設計思想（仕様書 §43/§45）: 目的は動画の量産ではなく、初心者に本当に役立つ解説を高品質で作ること。**基準未満なら投稿しない。**

---

## クイックスタート

依存パッケージのインストールは不要です（Phase 1 は Python 3.11 標準ライブラリのみで動きます）。

```bash
# 企画のみ（Phase 1）
python -m ai_navigator plan --topic "Claude Code vs Codex"

# 企画→台本まで一気に（Phase 1 + 2）
python -m ai_navigator run --topic "Claude Code vs Codex"

# 既存の企画ディレクトリから台本だけ（Phase 2）
python -m ai_navigator script --plan reports/2026-07-21_claude-code-vs-codex/
```

出力例:

```
✅ PRODUCE  (video)
Title     : Claude Code と Codex、あなたはこっち
Score     : 83/100   Fact: 100/100
Compare   : Claude Code vs Codex
------------------------------------------------
✅ Beginner QA : 100/100 (pass>=80, attempts=1)
✅ Fact QA     : 100/100 (7/7 claims, pass>=95)
```

レポートは `reports/YYYY-MM-DD_<slug>/` に書き出されます:

| ファイル | 内容 | フェーズ |
|---|---|---|
| `research.json` | 調査結果（Tier1〜4のソース・findings・初心者の疑問） | 1 |
| `ideas.json` | 企画10案（§9） | 1 |
| `critique.json` | 各案の欠点 最低5個（§10） | 1 |
| `scores.json` | 100点満点の採点＋判定（§11） | 1 |
| `selected_plan.json` | 採用案・理由・タイトル候補・ターゲット・比較対象（§44） | 1 |
| `sources.json` | 使用ソース一覧 | 1 |
| `script.json` | §17構成の台本（Opening→…→結論） | 2 |
| `script_tts.json` | TTS用の音声ユニット（§8: speed/pause/emphasis…） | 2 |
| `beginner_qa.json` | 初心者QA（§20: 用語/一文長/料金/結論… 0-100, <80再生成） | 2 |
| `fact_qa.json` | ファクトQA（各claimの根拠照合, 無根拠断定をflag） | 2 |

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
├── script/                  # ScriptWriter(§17) / TTSFormatter(§8) / BeginnerQA(§20) / FactQA(§13)
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
python tests/test_planning.py     # Phase 1（pytestなしで実行可能）
python tests/test_script.py       # Phase 2
# または pytest を入れて: pytest -q
```

---

## Phase 2: Script System（§17/§8/§20/§13）

`run` は企画で採用された案を台本化します。QAは**ルールベース（純コード）**で、mock/実LLMのどちらでも本物の検査が効きます。

```
selected_plan + research → ScriptWriter(§17) → TTSFormatter(§8) → BeginnerQA(§20) → FactQA(§13/§17)
                                 ▲                                       │ <80点なら
                                 └──────────── 再生成ループ ──────────────┘
```

- **ScriptWriter**: §17構成（Opening≤15sで一部先出し→…→必ず結論）。`用途によります`等の濁した結論は禁止（§18）。emit した専門用語には§19の平易な説明を自動付与。
- **TTSFormatter**: 台本をそのまま読まず、文単位の音声ユニットに整形（§8）。ツール名・専門用語を強調、場面転換で長めのポーズ。
- **BeginnerQA**: 用語説明/一文長/具体例/料金/使い始め方/結論明確 を採点（0-100）。80未満は再生成（最大3回）。
- **FactQA**: `is_claim` の行を research/ツールDBと照合し、根拠不明の断定を flag（§17「公式確認なしの断定」禁止）。

## ロードマップ

- **Phase 1**: Research + Planner ✅
- **Phase 2**: Script System（台本 / TTS整形 / Beginner QA / Fact QA）✅
- Phase 3: Voice + Storyboard（VOICEVOX / 字幕タイムコード / Scene分割）
- Phase 4: 動画生成（Remotion / FFmpeg）
- Phase 5: Browser Capture（Playwright 実操作録画）
- Phase 6: Video QA / Phase 7: YouTube / Phase 8: Analytics

詳細は仕様書 §39 を参照。

---

## 注意

`data/tools/*.json` の内容は現状 **seed のプレースホルダ** です。実際の料金・仕様は公開前に公式ソースで再確認してください（仕様 §12/§13）。
