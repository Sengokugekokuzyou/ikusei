# AI Navigator YouTube Automation System — 実装仕様書 v1.0

> このファイルはコード内の参照（§9, §11 …）の一次資料です。原文をそのまま保存しています。
> Phase 1 の実装範囲は §12/§13/§9/§10/§11/§14/§19/§44 です。

## 0. 目的

AIに詳しくない人向けに、新しいAIが何なのか / 何に使えるのか / 誰に向いているのか / 他のAIとどう使い分けるのか / 実際にどう使うのか を分かりやすく解説するYouTube動画を、可能な限り完全自動で制作・投稿・改善する。

単なるAIニュースチャンネルにはしない。チャンネルの中心価値は「AIが増えすぎて分からない人の代わりに、調べて、試して、比較して、あなたはこれを使えばいいと答える」こと。

## 1. 最重要方針

- **ターゲット**: AI上級者ではなく、ChatGPTは知っている / Claude・Codex・Kimi等の名前は聞いたことがある / ベンチマークを見ても意味が分からない / 結局どれを使えばいいか分からない / 実際の使い方まで知りたい / 専門用語が多い動画は苦手、という層。
- **動画の約束**: すべての動画で視聴者が最後に (1)このAIは何ができるか (2)自分に必要か (3)他AIとの違い (4)どう使えばいいか (5)次に何をすればいいか を理解できること。
- **禁止方針**: ニュース単純読み上げ / ベンチ数値の羅列 / AI音声＋静止画だけの紙芝居 / 毎日投稿の目的化 / 価値の低いニュースの動画化 / 「用途による」で濁す / 用語を説明なしで使用 / 公式確認なしの断定 / Reddit・Xだけを事実扱い / 同一テンプレの量産 / 実在しないAI操作画面を生成映像で偽装。

## 2. コンテンツ構成（長期比率）

- 40% Evergreen / 使い分け
- 30% 新AI・アップデート解説（「発表されました」ではなく「普通の人に何が変わる？」へ変換）
- 20% 実演・比較・対決
- 10% 純ニュース（重要のみ）

## 3. システム全体構成

情報収集 → 候補抽出 → 需要判定 → 初心者視点の疑問抽出 → 企画10案 → 全案ダメ出し → 最適案選択 → ファクトチェック → 必要なら実機テスト → 台本 → 初心者QA → Storyboard → TTS → 操作映像収録 → 図解/モーション → 動画編集 → 動画QA → サムネ → タイトル → 非公開アップロード → 承認 → 公開 → Analytics → 次回改善。

## 4–8. 技術

- Orchestrator: Python（実行/JSON管理/API/スケジューリング/エラー/再試行）
- 動画: Remotion（メイン）+ FFmpeg（補助）
- ブラウザ操作収録: Playwright（規約遵守、CAPTCHA突破しない）
- ナレーション: VOICEVOX優先、将来ElevenLabs等
- 音声設計: 台本をそのまま読まない。text/speaker/speed/pause_after/emotion/emphasis を持つ内部形式。

## 9. 企画生成エンジン

ニュース/テーマ1件につき最低10案。（例: 新機能まとめ / ChatGPT比較 / Claude比較 / 初心者向け / 使ってみる / 使い方5つ / Web制作 / 無料範囲 / 乗り換え / 結局何に使うか）

## 10. Critic工程

各案に最低5つの欠点。評価項目: 競合が強すぎないか / 初心者向けか / 結論が出せるか / 動画映えするか / 情報価値があるか / 長期検索されるか / 量産AI動画に見えないか。

## 11. 企画採点

100点満点: 初心者価値25 / 実用性20 / 検索需要15 / 話題性10 / 比較需要10 / 動画映え10 / 差別化5 / 情報信頼性5。判定: 80以上→通常動画候補 / 65〜79→Shorts候補 / 64以下→廃棄。動画化対象がなければ投稿しない。

## 12. Researcher

- Tier 1 公式（OpenAI/Anthropic/Google/Moonshot AI/GitHub/各公式Doc/Release Notes）
- Tier 2 信頼できるTech Media
- Tier 3 YouTube
- Tier 4 Reddit / X（ユーザーの反応・困りごととして利用。事実根拠にはしない）

## 13. Fact Checker

公開日 / 料金 / 対応OS / 無料プラン有無 / API有無 / 利用可能地域 / 日本語対応 / 商用利用 / 最新バージョン / 公式記載との一致 をチェック。動画制作日をmetadataに記録。

## 14. AI Tool Database

各AIの最新状態をDB化: `tool, category, updated_at, pricing, strengths, weaknesses, best_for, not_for, official_sources`。

## 15–16. Benchmark（Coding AI）

Test A 初心者向けTodoアプリ / B Bug修正 / C 既存プロジェクト機能追加 / D Screenshot→UI / E コード解説 / F 複数タスク自律実行。評価: Coding能力/既存理解/自律性/Visual理解/初心者向け/導入難易度/速度/エラー耐性/説明能力/価格性能。

## 17–18. Script Writer

構成: Opening(15秒以内に誰なら何を使えばいいか一部先出し) → Beginner Explanation → What Can It Do? → Real Demo → Comparison → Recommended For → Not Recommended For → Final Decision(必ず結論)。禁止する結論: 「どれも良いので用途によって選んでください」。代わりに「○○する人→Claude Code」等と明確化。

## 19. Beginner Translator

用語自動変換。CLI→文字でパソコンに指示を出す画面 / Repository→プログラム一式が入った作業場所 / Agent→自分である程度考えながら作業を進めるAI / Token→AIが文章を処理するための細かい単位。

## 20. Beginner QA

台本完成後に別AIで確認（用語説明/一文の長さ/迷わないか/具体例/料金説明/使い始め方/選ぶ物が分かるか/行動できるか）。80点未満なら再生成。

## 21–24. Storyboard / 映像

- 台本1文または1セクションごとに映像指示（scene_id, duration, voice, visual_type, animation, camera …）。
- 映像比率目標: 実操作35〜45% / モーション図解20〜30% / 比較カード15〜20% / B-roll5〜15% / 完全静止画最大10%。
- 同じ完全静止画を6秒以上出さない（Zoom/Pan/Highlight/Arrow/Cursor/Crop/Text Animation/PiP）。
- AIサービス解説は本物の操作画面優先。架空UIを実画面のように見せない。

## 25. モーションコンポーネント（Remotion共通部品）

ToolIntroCard / VSComparison / WinnerBadge / FeatureList / ProsConsCard / BeginnerTip / PriceCard / ScoreBar / RadarChart / WorkflowDiagram / StepByStep / FinalRecommendation / BreakingNews / ToolLogoTransition。

## 26–28. BGM/SE/字幕

BGMは常時小さめ・ナレーション最優先。SEは過度に使わない。字幕は基本あり、全文常時大字幕はしない、重要語を強調。

## 29–30. Video QA / 再生成

Technical（映像破損/音切れ/無音/黒画面/字幕欠け/音ズレ/解像度）、Content（事実誤認/料金/古い情報/用語/結論不明/音声不一致）、Retention（同じ映像が長い/冒頭が遅い/前置き/重複）。FAIL条件: 初心者理解<80 / Fact<95 / Visual variation<80 / Audio<90 / Conclusion clarity<90。FAIL時は問題部分のみ修正して再レンダリング。

## 31–32. タイトル/サムネ

タイトル最低20候補（検索性/クリック意欲/初心者理解/内容一致/誇張度、過剰煽り禁止）。サムネ: 大きい疑問/AI名/比較なら2〜3ツール/文字2〜5語/スマホで判読可能。

## 33–34. YouTube投稿/公開フェーズ

YouTube Data API。最初はPrivate/Unlisted、自動公開禁止。最初の10〜20本は完全自動制作＋人間が最終公開承認。品質安定後に条件付き完全自動公開。

## 35–37. Analytics/学習/改善

取得: Impressions/CTR/Views/Average View Duration/Average Percentage Viewed/30秒維持率/Subscribers gained/Traffic source（可能なら離脱位置）。動画ごとに topic_type/title_pattern/thumbnail_pattern/video_length/ctr/avg_percentage/first_30sec_retention を保存。Analytics AIが要因を評価し次回Plannerへフィードバック。

## 38. プロジェクト構造（原案）

collector / research / planner / benchmark / database / script / storyboard / capture / voice / video / thumbnail / qa / youtube / config / logs / orchestrator。

## 39. 実装フェーズ

- Phase 1 Research + Planner（最初に作る）
- Phase 2 Script System
- Phase 3 Voice + Storyboard
- Phase 4 動画生成
- Phase 5 Browser Capture
- Phase 6 Video QA
- Phase 7 YouTube
- Phase 8 Analytics

## 40–45. MVP / 優先順位

- MVP: 1ニュース入力 → 調査 → 企画10案 → Critic → 最適案 → 初心者台本 → Storyboard → 音声 → Remotion動画。YouTube投稿は後回し可。
- 最初のE2Eテーマ: 「Claude CodeとCodex、結局どっち？」
- 成功基準: 専門知識なしで理解 / 音声自然 / 静止画動画に見えない / 実操作映像 / 比較明確 / おすすめ対象が分かる / 人間編集不要。
- 最重要命令: 目的は量産ではなく、初心者に役立つ高品質解説を人間編集なしで作ること。基準未満なら投稿しない。
- 優先順位: 品質 » 事実性 » 初心者理解 » 映像品質 » 自動化率 » 投稿頻度。投稿頻度を最優先にしない。

### 44. 開発開始指示（Phase 1）

1 ディレクトリ作成 / 2 config設計 / 3 Tool Database schema / 4 Research output schema / 5 Planner schema / 6 Critic schema / 7 Scoring engine / 8 Judge / 9 Fact Checker / 10 CLI。

CLI例: `python -m ai_navigator plan --topic "Claude Code vs Codex"`。
出力: `reports/YYYY-MM-DD_claude-code-vs-codex/{research,ideas,critique,scores,selected_plan,sources}.json`。

## 46–73. 画像生成（OpenAI）追加仕様

- §46 画像生成はOpenAIを正式採用。Claude Code/Orchestratorが監督役として画像生成APIを自動実行。
- §49 実在サービスのUI/設定/料金/Dashboard/操作結果は生成画像で代用禁止。必ず本物のキャプチャ。
- §50–60 Image Director / Prompt Generator / 構図（余白確保）/ 画像内文字はRemotion側 / 再利用禁止 / Image QA(85未満再生成) / 最大3回再生成、失敗時はMotion Graphicへ切替 / 生成画像は静止3秒以上禁止・カメラモーション必須。
- §61–64 Thumbnail Director / Visual Rule / AB案 最低3案 / Thumbnail Judge。
- §65–66 image_generator/{director,openai,qa,assets} と thumbnail/{director,generator,judge} を追加。
- §67 API Keyは.env等。Gitへ絶対にCommitしない。
- §68–69 コスト記録とCost Guard（max_images_per_video 等）。
- §70 素材優先順位: 実操作映像 > 実結果画面 > Remotion > OpenAI生成画像 > 一般B-roll。
- §71–73 完全自動化（人手でChatGPTに依頼する設計は禁止）。実在サービスの仕様/操作/結果は本物の画面を優先。

## 役割分担

Claude Code=監督・編集長・自動化 / OpenAI Image Generation=美術・B-roll・Thumbnail / Playwright=カメラマン / VOICEVOX=ナレーター / Remotion=映像編集・Motion / FFmpeg=仕上げ・Encode。
