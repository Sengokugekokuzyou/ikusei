# AI Navigator

AIに詳しくない人向けに「増えすぎたAIを、調べて・試して・比較して "あなたはこれを使えばいい" と答える」YouTube動画を、可能な限り自動で制作・改善するためのシステムです。

このリポジトリは **Phase 1〜3** の実装です。1つのトピックを入力すると、調査 → ファクトチェック → 企画10案 → ダメ出し → 採点 → 判定 → 台本 → TTS整形 → 初心者QA → ファクトQA → 音声合成 → 絵コンテ → 字幕 までを自動で行い、人間がレビューできる形でレポートを出力します。

> 設計思想（仕様書 §43/§45）: 目的は動画の量産ではなく、初心者に本当に役立つ解説を高品質で作ること。**基準未満なら投稿しない。**

---

## クイックスタート

依存パッケージのインストールは不要です（Phase 1 は Python 3.11 標準ライブラリのみで動きます）。

```bash
# 企画のみ（Phase 1）
python -m ai_navigator plan --topic "Claude Code vs Codex"

# 企画→台本→音声→絵コンテ→字幕→サムネ（Phase 1-3 + サムネ）
python -m ai_navigator run --topic "Claude Code vs Codex"

# さらに mp4 まで一気に（Phase 4も）
python -m ai_navigator run --topic "Claude Code vs Codex" --video

# 既存ディレクトリから mp4 だけ生成（Phase 4）
python -m ai_navigator video --plan reports/2026-07-21_claude-code-vs-codex/
```

> `--video` / `video` は **フルffmpeg** が必要です。無料で入ります: `pip install imageio-ffmpeg`。

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
| `voice.json` + `voice/*.wav` | 音声合成マニフェスト＋クリップ（§7/§8、mockは無音WAV） | 3 |
| `storyboard.json` | 絵コンテ（§21-24: Scene/visual_type/component/camera/params） | 3 |
| `subtitles.json` + `captions.srt` | 字幕トラック（§28、音声タイミングに整合） | 3 |
| `thumbnails.json` + `thumbnails/*.png` | サムネ候補3案＋選定（§61-64、Chromiumで1280×720生成） | 画像 |
| `video.mp4` + `video.json` | 完成動画（§4-5、H.264+AAC、音声・字幕・モーション焼込み） | 4 |

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
├── voice/                   # VoiceAdapter(§7: mock/voicevox) / VoiceSynthesizer(§8)
├── storyboard/              # StoryboardBuilder(§21-24) / SubtitleBuilder(§28)
├── thumbnail/               # ThumbnailDirector(§62) / ChromiumRenderer(§54,61) / Judge(§64)
├── video/                   # SceneFrames(§25) / Ken Burns + narration + 字幕焼込み(§4-5)
├── capture/                 # Playwright録画 + カーソル合成(§5-6) / §49準拠デモ
├── image/                   # ImageDirector(§50) / providers(pixabay/openverse) / 引用対応(§48/§49)
├── htmlrender.py            # 共通 HTML→PNG（Chromium、サムネ/動画フレーム共用）
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
python tests/test_media.py        # Phase 3
python tests/test_thumbnail.py    # サムネイル
python tests/test_video.py        # Phase 4（ffmpeg/Chromium無ければ該当分スキップ）
python tests/test_capture.py      # Phase 5（Playwright無ければ該当分スキップ）
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

## Phase 3: Voice + Storyboard（§7/§8/§21-24/§28）

台本を音声タイムラインに載せ、絵コンテと字幕を導出します。LLM層と同じく**アダプタ方式**で、VOICEVOXエンジンが無くても動きます。

- **VoiceSynthesizer**: 各音声ユニットをアダプタで合成し、単一タイムラインに配置（§8のポーズ込み）。`mock`アダプタは推定尺の**無音WAVを実ファイル出力**するのでオフラインで完結、FFmpeg/Remotionの実入力になる。`voicevox`アダプタは稼働中エンジンにHTTP接続（`VOICEVOX_ENDPOINT`）。

### 実音声を出す（VOICEVOX・無料）

`mock` は無音です。実際に喋る動画にするには、無料の VOICEVOX エンジンを起動して切り替えます。

```bash
# 1) エンジンを起動（Docker。デスクトップアプリでも可、同じAPIを :50021 で提供）
docker run --rm -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest

# 2) 話者IDを確認（好きな声を選ぶ）
python -m ai_navigator speakers

# 3) 実音声に差し替え（尺が変わるので字幕・絵コンテも自動で再タイミング）
#    config を編集せず CLI で上書き指定できる：
python -m ai_navigator voice --plan reports/2026-07-21_.../ --adapter voicevox --speaker 3
python -m ai_navigator video --plan reports/2026-07-21_.../
```

`--endpoint http://HOST:50021` で別ホストのエンジンも指定可。config で恒久設定するなら
`[voice] adapter = "voicevox"` / `speaker = N`。

**企画から声つき動画まで一括**（VOICEVOX起動中）:
```bash
python -m ai_navigator run --topic "Claude Code vs Codex" --video --voicevox --speaker 3 --open
```
VOICEVOXに繋がらない場合は自動で無音(mock)にフォールバックして続行します。

> **VOICEVOX を動かすマシンと同じ場所でこのコマンドを実行してください。** 別マシン（例：ホスト型セッション）からローカルの `:50021` には到達できません。

### Windows でコマンドが苦手な方へ

**ダブルクリックだけ**で作れます → **[docs/windows-quickstart.md](docs/windows-quickstart.md)**（Python導入〜`scripts/make_video.bat` ダブルクリックまで、画像なしの手順）。

> **このリポジトリのホスト実行環境（Claude Code on the web）では実音声を生成できません。** egressポリシーが許可するのはパッケージレジストリ（PyPI/npm等）のみで、VOICEVOXエンジン/Dockerイメージ/各種TTS辞書の配信元（GitHub・Docker Hub 等）は403で拒否されます。**ローカルPC等、上記が取得できる環境で上記手順を実行すれば実音声になります**（アダプタは実装・配線済み）。
- **StoryboardBuilder**: 台本1行=1Sceneで、§25コンポーネント（VSComparison/FeatureList/ProsConsCard…）と§60カメラプリセット（cinematic_zoom/parallax_soft…）を割り当て。完全静止を作らない（§23）。§22の映像比率を自己申告し、実操作映像が目標未満なら警告。
- **SubtitleBuilder**: 音声タイミングに整合した字幕を生成（重要語をemphasisで保持、§28）。SRTも出力。

> mockは実操作映像を持たないため、§22の「実操作35〜45%」は必ず未達警告になります（正しい挙動）。実収録は Phase 5（Playwright）で補います。

## サムネイル & 画像（無料方針）

有料のOpenAI画像生成（§46-73）は使わず、**¥0・APIキー不要**で回します。仕様 §70 では生成画像は優先度4番目で、上位（実収録＋Remotionモーション）で代替できるためです。

- **サムネイル（§61-64）**: HTML/CSSで組み、**同梱のChromiumで1280×720 PNGに書き出し**。§54「文字は焼き込まず後載せ」に一致し、日本語（IPAGothic）も正確。ディレクター（§62）が最低3案を生成、ルールベースのJudge（§64）が選定。
- **B-roll / 背景（§48）**: シーン背景に**実写や公式スクショ**を合成できます（下記）。

`config` は `[image] provider = "none"` / `[thumbnail] renderer = "chromium"`。Chromiumは自動検出（`thumbnail.chrome_path`で明示も可）。

### 実写B-roll & 公式画像の引用（§48/§49/§70）

「手作りカードだけ」を脱するため、人物/背景の**実写B-roll**や、**公式スクショ・公式Xの引用**をシーン背景に合成します（暗いオーバーレイで文字は読みやすいまま、出典キャプション付き）。

```bash
# 無料ストック/CCから自動取得（openverse=キー不要, pixabay=要無料キー）
python -m ai_navigator images --plan reports/2026-07-21_.../ --provider openverse
python -m ai_navigator video  --plan reports/2026-07-21_.../
```

| provider | 中身 | ライセンス | キー |
|---|---|---|---|
| `none`(既定) | 取得しない（`assets/`のローカル画像だけ使用） | — | 不要 |
| `openverse` | CC画像 | 帰属必要（`credits.txt`に自動収集） | 不要 |
| `pixabay` | 商用安全な写真 | 帰属不要 | `PIXABAY_API_KEY`（無料） |

**公式スクショ・公式Xの引用**（Kimi等、手元に無いツールも）: `assets/scene_<番号>.jpg` を置き、`assets/scene_<番号>.txt` に出典（例:`出典: OpenAI 公式発表 https://...`）を書くと、そのシーン背景に使われ、**画面右下に出典を表示**（著作権法§32「引用」の出典明示）。`ImageDirector` は人物/概念シーンだけに画像を割当て、比較カードや実演（実収録）は据え置き。**架空UIの偽装はしません（§49）**。クレジットは概要欄用に `credits.txt` を自動出力。

## Phase 4: 動画生成（§4-5、FFmpegベース・無料）

絵コンテ＋音声＋字幕を実際の **mp4** にします。有料のRemotion/クラウドは使わず、Chromium（フレーム描画）＋フルffmpeg（エンコード）で¥0。

```
storyboard → 各Sceneをフレーム画像に描画(§25) → Ken Burnsモーション(§23/§58)
          → narration.wav合成(§8) + 字幕焼込み(§28) → video.mp4 (H.264+AAC)
```

- **フレーム**: 各SceneをHTML/CSSでComponent風に描画→Chromiumで1280×720 PNG。
- **モーション**: ffmpeg `zoompan` でシーンごとに zoom-in / zoom-out / pan を切替（完全静止を作らない §23）。
- **音声**: 各ユニットWAVをタイムライン通りに連結（stdlib、§8のポーズ込み）。
- **字幕**: `captions.srt` を `subtitles` フィルタで焼込み。日本語はスペースが無く自動改行できないため、~20字で改行。

E2E「Claude Code vs Codex」→ **1280×720@30fps・1分41秒・H.264+AAC**、音声/字幕/モーション入りの `video.mp4` を生成。フルffmpegは `pip install imageio-ffmpeg` で無料導入（同梱Playwright版はwebm専用で不可）。

## Phase 5: 実操作録画（§5-6、Playwright・無料）

`real_demo` シーンを、**実際の画面操作の録画**に差し替えます（§22の実操作映像、§70優先度1）。

```bash
python -m ai_navigator capture --plan reports/2026-07-21_.../   # 録画→mp4化
python -m ai_navigator video   --plan reports/2026-07-21_.../   # 該当シーンに合成
```

- **CaptureRecorder**: 同梱ChromiumをPlaywrightで駆動し、ページ操作（プロンプト入力→実行クリック→結果表示）を録画。ヘッドレスにはカーソルが無いので、**カーソルのドット＋クリック時のリップル**をJSで注入（§5 cursor highlight）。webm→1280×720 H.264 mp4に変換し、`real_demo`シーンへナレーション尺に合わせて合成。
- **§49 厳守**: 同梱デモは「収録デモ（プレースホルダ）— 実在サービスの画面ではありません」と明示したローカルページを録画します。**架空UIを実サービスに見せかけません**。

> **実在AIサービス（Claude Code / Codex / ChatGPT 等）の操作録画は、各自のログイン済みローカル環境で recipe を差し替えて行ってください。** このホスト環境ではegressポリシーで外部サイトが403、かつログイン/規約(§6)の制約があるため、実サービスは録画できません（フレームワークは実装済み）。

## ロードマップ

- **Phase 1**: Research + Planner ✅
- **Phase 2**: Script System（台本 / TTS整形 / Beginner QA / Fact QA）✅
- **Phase 3**: Voice + Storyboard（音声合成 / 絵コンテ / 字幕）✅
- **Phase 4**: 動画生成（FFmpegベースの mp4 出力）✅ ／ Remotion高品質版は将来（Node.js）
- **Phase 5**: Browser Capture（Playwright 実操作録画 → real_demoシーンに合成）✅
- Phase 6: Video QA / Phase 7: YouTube / Phase 8: Analytics

詳細は仕様書 §39 を参照。

---

## 注意

`data/tools/*.json` の内容は現状 **seed のプレースホルダ** です。実際の料金・仕様は公開前に公式ソースで再確認してください（仕様 §12/§13）。
