# PROJECT_LOG — ai-news-collector 開発記録

最終更新: 2026-03-26（Phase 11追加）

---

## 概要

Amazon Brand Specialist（3年目）がAI系企業のSalesポジションへの転職を目指すための
AIニュース収集＆転職活動支援ダッシュボード。

---

## 開発経緯（時系列）

### Phase 1 — 基盤構築

**目的:** AIニュースを毎日自動収集してMarkdownレポートを生成する

**実装内容:**
- `config.py` — RSSフィード定義（FeedSourceデータクラス）
- `collector.py` — RSS/Atomフィード収集（feedparser + httpx）
- `summarizer.py` — キーワードマッチによるトピック分類（外部API不要）
- `reporter.py` — Markdownレポート生成
- `main.py` — CLI エントリーポイント（--hours, --feeds, --no-summary等）

**技術的決定事項:**
- Claude API不要に変更 → RSSのdescriptionをそのまま整形して表示
- 英語記事はタイトル＋概要をそのまま保持（翻訳なし）
- Python 3.13.3 を `C:/Program Files/Python313/` にインストール（Microsoft Store版は回避）

---

### Phase 2 — フィード優先順位の整理

**目的:** 転職活動に役立つ情報を優先表示する

**フィード構成変更:**
- カテゴリを `target_company` / `overseas` / `japan` に整理
- ターゲット企業（OpenAI/Anthropic/Google等）を最優先・多めに収集（max_articles=30）
- 競合AI企業を追加: Meta AI, Microsoft, Apple, Nvidia, Hugging Face, Mistral AI, Scale AI

**レポートセクション順序:**
1. 💼 転職活動チェックポイント（採用・資金調達・新プロダクト・組織変更を自動ハイライト）
2. 🎯 転職ターゲット企業の最新動向（企業別グループ表示）
3. 🌐 AI業界ニュース
4. 🇯🇵 日本語AIニュース
5. 📌 トピック別インデックス

---

### Phase 3 — HTMLダッシュボード化

**目的:** ブラウザで見やすいダッシュボードを作る（サーバー不要）

**実装内容:**
- `dashboard.py` — 静的HTML生成（CSS/JS/データ全埋め込み・自己完結型）
- ダークテーマ・企業カラーコーディング
- タブ構成: 📰ニュース / 💼求人情報
- ニュースタブ: カテゴリ・企業・トピック・キーワードフィルタ
- ⭐ 転職関連記事のバッジ表示

**モバイル対応:**
- レスポンシブCSS（画面幅600px以下対応）
- Google Driveへのファイル同期でスマホからも閲覧可能

---

### Phase 4 — 求人情報収集の追加

**目的:** ダッシュボードに各社の求人情報を直接表示する

**実装内容:**
- `job_collector.py` — 各社ATSからの求人取得

**ATS別の実装方法:**

| 企業 | ATS | APIエンドポイント |
|------|-----|-----------------|
| OpenAI | Ashby | `api.ashbyhq.com/posting-api/job-board/openai` |
| Anthropic | Greenhouse | `boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true` |
| Google DeepMind | Greenhouse | `boards-api.greenhouse.io/v1/boards/deepmind/jobs?content=true` |
| Mistral AI | Lever | `api.lever.co/v0/postings/mistral?mode=json` |
| Scale AI | Greenhouse | `boards-api.greenhouse.io/v1/boards/scaleai/jobs?content=true` |

**躓いたポイント:**
- OpenAIはLeverからAshbyに移行済み → URLを修正
- Greenhouse APIは `?content=true` がないと部門情報が取得できない
- Lever APIはレスポンスがオブジェクトではなく配列を直接返す
- Google本社のCareers APIは非公開 → リンクカードのみ表示

---

### Phase 5 — 注目ソース（Priority Sources）の追加

**目的:** Bloomberg / FT / TechCrunch を別枠で目立つ表示にする

**試みたソース一覧:**
| ソース | 結果 |
|--------|------|
| Bloomberg Technology | ✅ 利用可能 |
| Financial Times Technology | ✅ 利用可能 |
| Reuters | ❌ 401認証エラー |
| 日経電子版 | ❌ 404 / 有料会員制 |
| Wired | ❌ 404 |

**実装変更:**
- `FeedSource` に `priority: bool = False` フィールド追加
- `Article` に `priority_source: bool = False` フィールド追加
- reporter.py: 🔥注目ソース速報セクションをレポート冒頭に追加
- dashboard.py: アンバー色のプライオリティバナーをニュースタブ上部に追加

---

### Phase 6 — 🏢 企業カルテタブの追加

**目的:** Amazon Brand Specialist → AI企業Sales転職に特化した分析ビューを作る

**ユーザー情報:**
- 現職: Amazon Brand Specialist（3年目）
- 転職希望: OpenAI / Anthropic / Google DeepMind / Mistral AI / Scale AI のSalesポジション

**実装内容:**
- 新タブ「🏢 企業カルテ」を追加
- 企業ごとにパネルを切り替え表示

**各パネルの表示内容:**
1. **Sales採用おすすめ度**（★〜★★★★★）— Sales求人数ベース
2. **統計カード** — 総求人数・Sales求人数・リモート可・リモート率
3. **Sales部門内訳** — CSSバーチャートで部門別求人数
4. **✨ あなたにマッチ** — Amazon Brand Specialist経験と親和性の高い求人をハイライト
5. **Sales求人一覧** — マッチ度・新着順でソート、キーワード検索対応
6. **最新ニュース** — 各社のニュース動向
7. **💰 年収データ** — US/日本タブ切り替え

**Sales判定キーワード:**
`sales`, `account`, `business development`, `customer success`, `partner`, `commercial`, `enterprise`, `go-to-market`, `gtm`, `solution`, `pre-sales`, `channel`, `revenue`, など

**マッチキーワード（Amazon Brand Specialist向け）:**
`brand`, `account`, `marketplace`, `partner`, `strategic`, `enterprise`, `digital`, `channel`, `customer success`, `growth`, `e-commerce`, `retail`, `advertis` など

---

### Phase 7 — 年収データの追加（US + 日本）

**目的:** 転職判断に必要な年収情報をダッシュボードに埋め込む

#### 🇺🇸 アメリカ採用データ（RepVue / Glassdoor 調査）

| 企業 | 役職 | OTE（USD） | クォータ達成率 |
|------|------|-----------|------------|
| OpenAI | AE | $290K〜$300K | 80% |
| Anthropic | AE | $250K〜$545K | 85% |
| Google Cloud | AE | $225K〜$335K | 70% |
| Mistral AI | AE (US) | $240K〜$300K（推定） | 98%（少数データ）|
| Scale AI | AE | $350K〜$360K | **39%**（⚠️要注意）|

#### 🇯🇵 日本採用データ（OpenWork / Levels.fyi Tokyo / 求人票調査）

| 企業 | 日本オフィス | Sales採用状況 | OTE目安（万円） |
|------|------------|------------|--------------|
| Anthropic | ✅ 2025年10月開設 | 🔥 積極採用中（EAE複数名） | ¥1,000万〜¥1,800万（推定） |
| OpenAI | ✅ 2024年4月開設 | Account Director募集 | ¥1,200万〜¥2,000万（推定） |
| Google Cloud Japan | ✅ 大規模組織 | 安定採用 | ¥1,300万〜¥2,054万（実績値） |
| Mistral AI | ❌ なし | 日本採用なし | — |
| Scale AI | ❌ なし | 日本採用なし | — |

**現職比較（Amazon Brand Specialist 3年目）:** ¥800万〜¥1,100万（概算）

#### 重要な注意事項
- アメリカ採用とJapan採用では**1/3〜1/2程度の年収差**がある
- Amazon 3年目は**4年目に40%のRSUがベスト**する重要なタイミング → 転職時期の検討材料
- Scale AIのクォータ達成率39%は業界平均（75〜85%）を大きく下回る → 初転職先としてリスク高

#### おすすめ転職ルート

**最短ルート:** Anthropic Japan EAE（今が採用タイミング・Amazon経験が直結）

**安定ルート:** Salesforce Japan / AWS Japan でBDR→AE経験（1〜2年）→ AI企業AEへ

**横滑りルート:** Google Cloud Japan CSM（Amazonアカウント管理経験が活きる）

---

### Phase 8 — 企業分析（3C / SWOT / 4P）の追加

**目的:** 各社の市場ポジションを構造的に把握し、面接対策に活用する

**実装内容:**
- `dashboard.py` に `COMPANY_ANALYSIS` 定数を追加（5社分・手動調査データ）
- 企業カルテタブの各パネル内に「📊 企業分析」セクションを追加
- 4タブ切り替えUI: **3C分析 / SWOT分析 / 4P分析 / 💬 面接対策**

**データ出所:** RepVue・Glassdoor・各社公式IR・TechCrunch・Bloomberg・SaaStr 等（2025-2026）

#### 各社分析サマリー

| 企業 | tagline | 特記事項 |
|------|---------|---------|
| OpenAI | ChatGPTで世界最大のコンシューマー＆エンタープライズAIブランド | ARR $20B・9億WAU・BainパートナーEコシステム |
| Anthropic | 安全性重視・エンタープライズ特化の急成長AIラボ | ARR $19B・Claude Code $2.5B・クォータ持ち営業~18名 |
| Google DeepMind | 最大のインフラ・データ基盤を持つAIのフルスタックプレイヤー | Cloud ARR $15.2B/Q・受注残高$240B・Workspace 4,500万組織 |
| Mistral AI | 欧州発・オープンソース戦略で価格破壊を武器にするチャレンジャー | ARR $400M・競合の20%価格・EU主権AI |
| Scale AI | AIデータファウンドリから政府・防衛向けAIプラットフォームへ進化中 | 売上$870M・DoD Donovan・Meta 49%株取得後の転換期 |

#### 3C分析の視点
- **Company（自社）**: コア技術・製品・ビジネスモデル・市場ポジション
- **Customer（顧客）**: 主要セグメント・購買プロセス・主要ユースケース
- **Competitor（競合）**: 競合企業・勝ちパターン・負けパターン

#### SWOT の色分け
- 💪 Strengths → 緑（`#10b981`）
- ⚠️ Weaknesses → 赤（`#ef4444`）
- 🚀 Opportunities → 青（`#3b82f6`）
- 🔥 Threats → 黄（`#f59e0b`）

#### 4P の営業視点
- **Product**: 主力製品・機能・ティア構成
- **Price**: 価格モデル・API単価・エンタープライズ契約規模
- **Place**: 販売チャネル（直販・パートナー・マーケットプレイス）
- **Promotion**: GTMモーション・DeveloperEvangelism・エンタープライズ営業手法

#### 面接対策タブの内容
各社ごとに「なぜこの会社か」「競合との差別化」「Amazon経験の活かし方」「注意すべき反論準備」を4点でまとめた想定QAを収録。

**特に重要な面接インサイト:**
- **Anthropic**: ~18名のクォータ持ちで$19B ARRを支える→一人当たりの裁量の大きさをアピール
- **Scale AI**: Meta 49%投資後の顧客離脱（OpenAI・Google）への反論準備が必須
- **Google Cloud**: Amazon経験はAWS vs GCPの競合討議でリアルなインサイトになる強み
- **Mistral AI**: CFO・CISOへのコスト・セキュリティ訴求が主なセールスモーション

---

## 用語集（Salesポジション）

| 略語 | 正式名称 | 役割 |
|------|---------|------|
| AE | Account Executive（アカウントエグゼクティブ） | 担当顧客に直接販売する営業 |
| BDR | Business Development Representative | 新規リード開拓・アポ取りが主業務 |
| SDR | Sales Development Representative | インバウンドリード対応 |
| CSM | Customer Success Manager | 契約後の顧客支援・継続率向上 |
| OTE | On-Target Earnings | 目標達成時の基本給＋コミッション合計 |
| GTM | Go-To-Market | 市場進出戦略 |
| クォータ | Quota | 担当者ごとの売上目標額 |

---

## 技術スタック

| 用途 | ライブラリ・技術 |
|------|---------------|
| HTTPクライアント | httpx |
| RSSパーサー | feedparser |
| HTMLパース | BeautifulSoup4 |
| フロントエンド | Vanilla JS + CSS（フレームワーク不使用） |
| データ受け渡し | JSON（HTMLにインライン埋め込み） |
| Python | 3.13.3（C:/Program Files/Python313/） |

---

### Phase 9 — GitHub自動プッシュ＆パス修正（2026-03-23）

**目的:** `main.py` 実行後に自動でGitHub Pagesへデプロイする

**実装内容:**
- `main.py` に `_git_push()` 関数を追加（`git add reports/ → commit → push` を自動実行）
- `config.py` の `OUTPUT_DIR` を絶対パスに変更（PowerShellのカレントディレクトリ問題を解決）
- `subprocess` モジュールを使用

**解決した問題:**
- PowerShellを `C:\Users\arenn\` から実行するとreportsが別ディレクトリに生成されていた
- `git add` でパス不一致エラーが出ていた → `reports/` 全体をaddするよう変更

---

### Phase 10 — 広告業界版ダッシュボード追加（2026-03-25）

**目的:** AIスタートアップに加えて広告業界（Google/Meta/Microsoft）の企業カルテ・求人を表示

**実装内容:**
- `dashboard.py` に `AD_SALARY_DATA`、`AD_SALARY_DATA_JP`、`AD_COMPANY_ANALYSIS` を追加
- 企業カルテタブに「🤖 AIスタートアップ / 📺 広告業界」切り替えボタンを追加
- `job_collector.py` に `fetch_google_jobs()`、`fetch_meta_jobs()`、`fetch_microsoft_jobs()` を追加

**制約・判断:**
- Google/Meta/Microsoftは求人APIが非公開のため、公式キャリアページへのリンクカード（各社4件）として実装
- `_company_profile_json()` の戻り値を `{"ai": ..., "ad": ...}` 構造に変更

---

### Phase 11 — index.htmlリダイレクト＆タスクスケジューラ（2026-03-26）

**目的:** 固定URLでいつでも最新ダッシュボードにアクセスできるようにする

**実装内容:**
- `index.html` を作成（JavaScriptで今日の日付のダッシュボードURLに自動リダイレクト）
- `run_daily.bat` を作成（タスクスケジューラ用バッチファイル）
- `main.py` の `git add` 対象に `index.html` を追加

**アクセスURL:** `https://aren8679.github.io/ai-news-collector/`

---

### Phase 12 — GitHub Actions自動実行（2026-03-26）

**目的:** PCの電源不要で毎朝7時に自動でダッシュボードを更新する

**実装内容:**
- `.github/workflows/daily.yml` を作成
  - スケジュール: 毎日 22:00 UTC（= 翌朝 7:00 JST）
  - `workflow_dispatch` で手動実行ボタンも有効化
  - GitHubサーバー上でPython実行 → `git commit & push` まで自動
- `main.py` の `_git_push()` にCI環境スキップ処理を追加
  - `GITHUB_ACTIONS` または `SKIP_GIT_PUSH` 環境変数があればgit push をスキップ
  - ローカル実行時は従来通り自動プッシュ
- `import os` を `main.py` に追加

**GitHub側の設定:**
- Settings → Actions → General → Workflow permissions → **Read and write permissions** に変更が必要

**結果:** PCの電源・ネット接続不要。スマホから固定URLで毎朝最新ダッシュボードにアクセス可能。

---

## 既知の問題・制限事項

| 問題 | 状況 |
|------|------|
| Anthropic Blog RSSが不安定 | 404になる場合があり（フィードURLが変わる可能性） |
| AI-SCHOLAR XML不正 | feedparserが警告を出すが記事はゼロ件で継続 |
| Ledge.ai 404 | フィードURL変更済み・要更新 |
| 年収データは推定値含む | 特にOpenAI Japan・Anthropic Japanは公式データなし |
| 日経・Reuters RSS | 認証必須のため取得不可 |

---

## 実行方法

### 自動実行（推奨）
GitHub Actionsが毎朝7時（JST）に自動実行。PC不要。
→ `https://aren8679.github.io/ai-news-collector/` をブックマークするだけ

### 手動実行（Windows PowerShell）
```
& "C:/Program Files/Python313/python.exe" D:/ai-news-collector/main.py
```

### GitHub Actionsで手動トリガー
1. `https://github.com/aren8679/ai-news-collector` → Actions タブ
2. Daily Dashboard Update → Run workflow
