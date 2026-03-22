# AI News Collector

AIニュース自動収集＆転職活動支援ダッシュボード。
RSSフィードから記事を収集し、HTMLダッシュボードとMarkdownレポートを毎日生成する。

> **外部APIキー不要** — Claude API等の有料サービスへの依存なし。

---

## 主な機能

| 機能 | 概要 |
|------|------|
| 📰 RSSニュース収集 | OpenAI/Anthropic/Google等の公式ブログ＋業界メディア |
| 🔥 注目ソース速報 | Bloomberg / Financial Times / TechCrunch を別枠表示 |
| 💼 転職活動チェックポイント | 採用・資金調達・新プロダクト関連記事を自動ハイライト |
| 💼 求人情報収集 | OpenAI / Anthropic / Google DeepMind / Mistral AI / Scale AI の公開ATS |
| 🏢 企業カルテ | Sales職分析・年収データ（US/日本）・マッチ度ハイライト・3C/SWOT/4P分析・面接対策 |
| 📊 静的HTMLダッシュボード | サーバー不要・ブラウザで直接開ける |
| 📄 Markdownレポート | 日付ごとにファイル保存 |

---

## セットアップ

### 1. Python のインストール

Python 3.10以上（推奨: 3.13.x）を [python.org](https://python.org) からインストール。
Microsoft Store版ではなく **公式インストーラー版** を使用すること。

Windows での確認:
```
"C:/Program Files/Python313/python.exe" --version
```

### 2. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 3. 実行

```bash
"C:/Program Files/Python313/python.exe" main.py
```

`reports/` フォルダに以下が生成される:
- `YYYY-MM-DD_ai_news.md` — Markdownレポート
- `YYYY-MM-DD_dashboard.html` — HTMLダッシュボード

---

## 使い方

### 基本実行（全機能・24時間分）

```bash
python main.py
```

### オプション

```bash
# 要約処理をスキップ（高速確認用）
python main.py --no-summary

# 過去48時間分を収集
python main.py --hours 48

# カテゴリを絞る
python main.py --feeds overseas       # 海外ニュースのみ
python main.py --feeds official_blog  # 公式ブログのみ
python main.py --feeds japan          # 日本語ニュースのみ

# 出力先を指定
python main.py --output-dir /path/to/reports
```

---

## ダッシュボード構成

ブラウザで `reports/YYYY-MM-DD_dashboard.html` を開く。

### 📰 ニュースタブ
- 記事カード表示（カテゴリ・企業・トピック・キーワードでフィルタ）
- **🔥 注目ソース速報** セクション（Bloomberg / FT / TechCrunch）
- ⭐ 転職関連記事のハイライト

### 💼 求人情報タブ
- 各社のATS（採用管理システム）から取得した求人一覧
- 企業・部門・リモート・キーワードで絞り込み
- Google Careers は公式ページへのリンクカード

### 🏢 企業カルテタブ
- Sales職に特化した企業分析（OpenAI / Anthropic / Google DeepMind / Mistral AI / Scale AI）
- **🇺🇸 / 🇯🇵 タブ切り替え**で米国・日本の年収データを確認
- ✨ Amazon Brand Specialist 経験とのマッチ度ハイライト
- クォータ達成率・転職アドバイス付き
- **📊 企業分析セクション（3C / SWOT / 4P / 面接対策）**
  - `3C分析`: Company（自社）/ Customer（顧客）/ Competitor（競合）
  - `SWOT分析`: 強み🟢 / 弱み🔴 / 機会🔵 / 脅威🟡 の色分けグリッド
  - `4P分析`: Product / Price / Place / Promotion を営業視点で解説
  - `面接対策`: 各社ごとの想定QA（なぜここか・競合との違い・Amazon経験の活かし方）

---

## 収集ソース一覧

### 🔥 注目ソース（priority）
| ソース | URL |
|--------|-----|
| Bloomberg Technology | `feeds.bloomberg.com/technology/news.rss` |
| Financial Times Technology | `ft.com/technology?format=rss` |
| TechCrunch AI | `techcrunch.com/category/artificial-intelligence/feed/` |

### 🎯 転職ターゲット企業公式ブログ
| 企業 | フィード |
|------|---------|
| OpenAI | `openai.com/news/rss.xml` |
| Anthropic | `anthropic.com/news/rss` |
| Google DeepMind | `deepmind.google/blog/rss.xml` |
| Google AI | `blog.google/technology/ai/rss/` |
| Meta AI | `engineering.fb.com/category/ai-research/feed/` |
| Microsoft AI | `blogs.microsoft.com/ai/feed/` |
| Apple ML | `machinelearning.apple.com/rss.xml` |
| Nvidia | `blogs.nvidia.com/feed/` |
| Hugging Face | `huggingface.co/blog/feed.xml` |

### 🌐 AI業界ニュース
The Verge AI / Ars Technica / VentureBeat AI

### 🇯🇵 日本語AIニュース
AI-SCHOLAR / ITmedia AI+

### 💼 求人情報（ATS API）
| 企業 | ATS | 求人数（参考） |
|------|-----|--------------|
| OpenAI | Ashby | ~645件 |
| Anthropic | Greenhouse | ~437件 |
| Google DeepMind | Greenhouse | ~100件 |
| Mistral AI | Lever | ~143件 |
| Scale AI | Greenhouse | ~164件 |

---

## ファイル構成

```
ai-news-collector/
├── main.py           # エントリーポイント・パイプライン制御
├── collector.py      # RSSフィード収集
├── summarizer.py     # キーワードマッチによるトピック付与・要約整形
├── reporter.py       # Markdownレポート生成
├── dashboard.py      # HTMLダッシュボード生成
├── job_collector.py  # 求人情報収集（ATS API）
├── config.py         # RSSフィード設定・グローバル設定
├── requirements.txt
├── README.md
├── PROJECT_LOG.md    # 開発ログ
└── reports/          # 生成されたレポート・ダッシュボード
    ├── YYYY-MM-DD_ai_news.md
    └── YYYY-MM-DD_dashboard.html
```

---

## 設定パラメータ（config.py / 環境変数）

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `FETCH_HOURS` | `24` | 何時間前までの記事を取得するか |
| `MAX_ARTICLES_PER_FEED` | `10` | フィードあたり最大取得記事数 |
| `REQUEST_TIMEOUT` | `15` | HTTPタイムアウト（秒） |
| `OUTPUT_DIR` | `reports` | 出力ディレクトリ |

フィードごとに `max_articles` を個別設定可能（ターゲット企業は30件など）。

---

## 年収データについて（企業カルテ）

- **🇺🇸 US版**: RepVue / Glassdoor 調査データ（USD建て、2025-2026）
- **🇯🇵 日本版**: OpenWork / Levels.fyi Tokyo / 各社求人票調査（万円建て、2025-2026）
- データは推定値を含む。最新情報は各リンク先で確認すること。

---

## 今後の候補機能

- [ ] 新着求人の差分検知・アラート表示（前回実行との増減表示）
- [ ] 全社横断Sales求人ランキング（職種キーワード別）
- [ ] 職務経歴書キーワードアシスト（各社JDから頻出フレーズ抽出）
- [ ] arXiv論文数による企業研究力スコア
- [ ] Google Drive自動同期（モバイル閲覧対応）
- [ ] Notion連携
