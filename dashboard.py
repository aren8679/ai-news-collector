"""
Static HTML dashboard generator.
Produces reports/YYYY-MM-DD_dashboard.html — open directly in any browser.

Tabs:
  - ニュース    : article cards with category / topic / keyword filters
  - 求人情報    : job cards with company / department / location / keyword filters
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from collector import Article
from job_collector import Job, GOOGLE_CAREERS_URL
from config import OUTPUT_DIR
from summarizer import JOB_RELEVANT_TOPICS

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

CATEGORY_LABELS = {
    "target_company": "🎯 転職ターゲット企業",
    "overseas":       "🌐 AI業界ニュース",
    "japan":          "🇯🇵 日本語AIニュース",
}

TOPIC_BADGE_COLORS: dict[str, str] = {
    "採用・人事": "#7c3aed",
    "新プロダクト": "#dc2626",
    "資金調達":   "#d97706",
    "組織変更":   "#0891b2",
}

COMPANY_COLORS = {
    "OpenAI":         "#10a37f",
    "Anthropic":      "#c96442",
    "Google DeepMind": "#4285f4",
    "Google":         "#34a853",
    "Meta AI":        "#0866ff",
    "Microsoft":      "#00a4ef",
    "Apple":          "#555555",
    "Nvidia":         "#76b900",
    "Hugging Face":   "#ff9d00",
    "Mistral AI":     "#7b61ff",
    "Scale AI":       "#ff6b35",
}

# ---------------------------------------------------------------------------
# 企業カルテ — Sales分析
# ---------------------------------------------------------------------------
# Amazon Brand Specialist背景とマッチするキーワード
MATCH_KEYWORDS = [
    "brand", "account", "marketplace", "partner", "strategic", "enterprise",
    "digital", "channel", "customer success", "growth", "e-commerce", "retail",
    "advertis", "programmatic",
]

# Salesポジション判定キーワード
SALES_KEYWORDS = [
    "sales", "account executive", "account manager", "account director",
    "business development", "customer success", "partner", "commercial",
    "enterprise", "go-to-market", "gtm", "solution engineer", "solution architect",
    "pre-sales", "presales", "channel", "revenue", "field", "demand generation",
    "partnerships", "market development", "strategic account", "bd ", "alliances",
    "client", "customer", "growth", "segment", "region", "territory",
]


# ---------------------------------------------------------------------------
# 年収データ（RepVue / Glassdoor 調査済み、2025-2026）
# ---------------------------------------------------------------------------
SALARY_DATA: dict = {
    "OpenAI": {
        "repvue_url":   "https://www.repvue.com/companies/openai/salaries",
        "glassdoor_url":"https://www.glassdoor.com/Salary/OpenAI-Salaries-E2210885.htm",
        "quota_attainment": 80,
        "avg_quota_m":  1.475,
        "entry_advice": "AEへの直接応募は難しめ。まずBDR/SDRで入社し1〜2年でAEへ昇格が現実的なルート。",
        "match_level":  3,
        "roles": [
            {"role":"Account Executive",    "base_low":238, "base_high":245, "ote_low":290, "ote_high":300, "note":"82/18 Base-Variable"},
            {"role":"Enterprise AE",        "base_low":238, "base_high":245, "ote_low":290, "ote_high":310, "note":"上位実績者は$900K+"},
            {"role":"CSM",                  "base_low":150, "base_high":170, "ote_low":150, "ote_high":200, "note":"推定値"},
            {"role":"BDR / SDR",            "base_low": 80, "base_high": 95, "ote_low":300, "ote_high":320, "note":"チーム構築中・推定値"},
        ],
    },
    "Anthropic": {
        "repvue_url":   "https://www.repvue.com/companies/anthropic/salaries",
        "glassdoor_url":"https://www.glassdoor.com/Salary/Anthropic-Salaries-E8109027.htm",
        "quota_attainment": 85,
        "avg_quota_m":  1.35,
        "entry_advice": "BDRチームを現在積極採用中（8〜12名規模）。Amazonでのアカウント管理経験はCSMにも直結。最もマッチ度が高い。",
        "match_level":  5,
        "roles": [
            {"role":"Account Executive",    "base_low":135, "base_high":165, "ote_low":250, "ote_high":545, "note":"42/58 Base-Variable"},
            {"role":"Enterprise AE",        "base_low":168, "base_high":225, "ote_low":280, "ote_high":400, "note":""},
            {"role":"CSM",                  "base_low":110, "base_high":160, "ote_low":260, "ote_high":315, "note":"Mgr levelは$315K OTE"},
            {"role":"BDR / SDR",            "base_low": 70, "base_high": 90, "ote_low":110, "ote_high":140, "note":"現在チーム構築中★"},
        ],
    },
    "Google DeepMind": {
        "repvue_url":   "https://www.repvue.com/companies/GoogleCloud/salaries",
        "glassdoor_url":"https://www.glassdoor.com/Salary/Google-DeepMind-Salaries-E1596815.htm",
        "quota_attainment": 70,
        "avg_quota_m":  None,
        "entry_advice": "DeepMind自体にSales組織はなく、AIプロダクト販売はGoogle Cloud経由。プロセスが大企業的で時間がかかる。",
        "match_level":  2,
        "roles": [
            {"role":"AE (Google Cloud)",    "base_low":100, "base_high":150, "ote_low":225, "ote_high":335, "note":"43/57 Base-Variable"},
            {"role":"Enterprise AE",        "base_low":140, "base_high":140, "ote_low":325, "ote_high":325, "note":"上位実績者$1.06M"},
            {"role":"CSM (Google Cloud)",   "base_low":105, "base_high":212, "ote_low":160, "ote_high":355, "note":"56/44 split"},
            {"role":"BDR / SDR",            "base_low": 55, "base_high": 70, "ote_low": 90, "ote_high":130, "note":"60/40 split"},
        ],
    },
    "Mistral AI": {
        "repvue_url":   "https://www.repvue.com/companies/mistral-ai",
        "glassdoor_url":"https://www.glassdoor.com/Overview/Working-at-Mistral-AI-EI_IE9945031.11,21.htm",
        "quota_attainment": 98,
        "avg_quota_m":  None,
        "entry_advice": "米国GTMは2024〜2025年に立ち上げたばかりでグランドフロア狙いのチャンス。採用基準が柔軟な可能性大。ただし米国データが薄く注意。",
        "match_level":  4,
        "roles": [
            {"role":"Account Executive (US)","base_low":120,"base_high":150, "ote_low":240, "ote_high":300, "note":"米国推定値"},
            {"role":"CSM",                   "base_low":None,"base_high":None,"ote_low":None,"ote_high":None,"note":"米国データなし"},
            {"role":"BDR / SDR",             "base_low":None,"base_high":None,"ote_low":None,"ote_high":None,"note":"米国データなし"},
        ],
    },
    "Scale AI": {
        "repvue_url":   "https://www.repvue.com/companies/Scale/salaries",
        "glassdoor_url":"https://www.glassdoor.com/Salary/Scale-Salaries-E1656849.htm",
        "quota_attainment": 39,
        "avg_quota_m":  1.75,
        "entry_advice": "⚠️ クォータ達成率が39%と業界平均を大幅に下回る。転職直後の成果を出しにくい環境のため初転職先としてはリスク高め。",
        "match_level":  3,
        "roles": [
            {"role":"Account Executive",    "base_low":175, "base_high":215, "ote_low":350, "ote_high":360, "note":"52/48 split・上位$1.5M"},
            {"role":"Enterprise AE",        "base_low":175, "base_high":215, "ote_low":350, "ote_high":360, "note":""},
            {"role":"CSM",                  "base_low": 96, "base_high": 96, "ote_low": 92, "ote_high":147, "note":"Glassdoor報告値"},
            {"role":"BDR / SDR",            "base_low": 80, "base_high":100, "ote_low": 80, "ote_high":120, "note":"推定値"},
        ],
    },
}

# Amazon Brand Specialist（現職）の参考年収
AMAZON_COMP = {"base_low": 95, "base_high": 130, "note": "Amazon Brand Specialist 3年目（参考値）"}

# ---------------------------------------------------------------------------
# 日本市場 年収データ（万円建て、OpenWork / Levels.fyi Tokyo / 各社求人調査 2025-2026）
# ---------------------------------------------------------------------------
SALARY_DATA_JP: dict = {
    "OpenAI": {
        "has_office":    True,
        "hiring_status": "active",
        "office_note":   "2024年4月開設。アジア初拠点。元AWS Japan社長・長崎忠雄氏が代表。ハイブリッド勤務（週3出社）。",
        "entry_advice":  "Account Director職で即戦力採用が中心。直接応募はハードルが高め。Salesforce/AWS Japan経由で経験を積んでから狙うのが現実的。",
        "roles": [
            {"role": "Account Director",    "ote_low": 1200, "ote_high": 2000, "note": "⚠️ 推定値・公式データなし"},
        ],
        "openwork_url":  "https://www.openwork.jp/company.php?m_id=a0C2x00000bELGn",
    },
    "Anthropic": {
        "has_office":    True,
        "hiring_status": "actively_hiring",
        "office_note":   "2025年10月開設。東京オフィス。Enterprise AEを現在積極採用中（一般＋公共セクター）。",
        "entry_advice":  "⭐ 今が狙い目。Enterprise AEを複数名募集中。Amazonでのエンタープライズ顧客管理経験は直結しやすい。日本語ネイティブ必須。",
        "roles": [
            {"role": "Enterprise AE（一般）",          "ote_low": 1000, "ote_high": 1800, "note": "⚠️ 推定値（求人票に明記なし）"},
            {"role": "Enterprise AE（公共セクター）",   "ote_low": 1000, "ote_high": 1800, "note": "8年以上の日本企業営業経験必須"},
        ],
        "openwork_url":  None,
    },
    "Google DeepMind": {
        "has_office":    True,
        "hiring_status": "stable",
        "office_note":   "Google Cloud Japanが実質のSales窓口。東京に大規模な営業組織あり。",
        "entry_advice":  "Google Cloud Japanから応募。大企業ゆえ採用プロセスが長く3〜6ヶ月かかる場合も。SDR→AEの内部昇格パスあり。",
        "roles": [
            {"role": "AE（Google Cloud Japan）中堅",   "ote_low": 1300, "ote_high": 1800, "note": "OpenWork実績値"},
            {"role": "AE（Google Cloud Japan）シニア", "ote_low": 1800, "ote_high": 2054, "note": "OpenWork実績値"},
        ],
        "openwork_url":  "https://www.openwork.jp/company.php?m_id=a0C2x000008wtjU",
    },
    "Mistral AI": {
        "has_office":    False,
        "hiring_status": "none",
        "office_note":   "日本オフィスなし。Capgemini Japanがパートナー企業として対応。",
        "entry_advice":  "現時点で日本採用なし。米国・欧州採用がメイン。",
        "roles": [],
        "openwork_url":  None,
    },
    "Scale AI": {
        "has_office":    False,
        "hiring_status": "none",
        "office_note":   "日本オフィスなし。リモート・パートナー経由のみ。",
        "entry_advice":  "現時点で日本採用なし。",
        "roles": [],
        "openwork_url":  None,
    },
}

# 参考：外資IT企業 日本Sales年収ベンチマーク（万円）
JAPAN_BENCHMARK = [
    {"company": "Salesforce Japan", "role": "AE",     "ote_low": 900,  "ote_high": 2000, "note": "上位実績者¥3,000万〜"},
    {"company": "AWS Japan",        "role": "AE",     "ote_low": 845,  "ote_high": 2447, "note": "L4〜L6"},
    {"company": "外資IT全般",        "role": "BDR/SDR","ote_low": 500,  "ote_high": 900,  "note": "インサイドセールス"},
    {"company": "外資IT全般",        "role": "CSM",    "ote_low": 700,  "ote_high": 1500, "note": "カスタマーサクセス"},
]

AMAZON_COMP_JP = {"low": 800, "high": 1100, "note": "Amazon Brand Specialist 3年目 概算（現職・参考値）"}

# ---------------------------------------------------------------------------
# 企業分析データ（3C / SWOT / 4P）— 2025-2026 調査
# ---------------------------------------------------------------------------
COMPANY_ANALYSIS: dict = {
    "OpenAI": {
        "tagline": "ChatGPTで世界最大のコンシューマー＆エンタープライズAIブランド",
        "snapshot": "ARR $20B・従業員~4,500名・評価額$500B・調達総額$110B+",
        "c3": {
            "company": [
                "週間アクティブユーザー9億人・有料サブスクライバー900万人超のChatGPTが最大の資産",
                "GPT-5 / o3 / Sora / Operatorエージェントなどマルチモーダルのフルラインナップ",
                "MicrosoftのAzureインフラとBainコンサルパートナーシップがエンタープライズ展開を支える",
            ],
            "customer": [
                "エンタープライズ: ChatGPT Enterprise（最小150席・年間$108K〜）、大型案件はBain経由も",
                "SMB / チーム: ChatGPT Business（$30/ユーザー/月）セルフサーブ可能",
                "開発者: APIアクセス・スタートアップ向けクレジット・GPTストアエコシステム",
            ],
            "competitor": [
                "Anthropic（コーディング・安全性）、Google（インフラ・Workspace統合）、Meta Llama（オープンソース価格破壊）",
                "勝ちパターン: ChatGPTブランドと9億ユーザーのPLG基盤、エコシステムの深さ",
                "負けパターン: コーディング特化タスクはClaude、価格ではMeta Llama・DeepSeekに負ける",
            ],
        },
        "swot": {
            "strengths": [
                "ChatGPTの圧倒的ブランド認知と9億人のユーザー基盤",
                "GPT-5・o3など継続的な最先端モデルリリース",
                "Microsoft Azure統合によるエンタープライズ展開力",
                "マルチモーダル（テキスト・画像・音声・動画）の包括的プロダクト群",
            ],
            "weaknesses": [
                "Microsoft Azureへのインフラ依存（自社クラウド基盤なし）",
                "幻覚・誤情報問題が未解決で高精度業種（医療・法律）での信頼に課題",
                "急激な組織拡張による文化・ガバナンスの不安定性",
                "エンタープライズ営業チームが~107名と小規模で大型案件対応に限界",
            ],
            "opportunities": [
                "StarGate $500Bインフラ投資によるAGI時代の中核インフラ化",
                "医療・法律・教育など規制産業への垂直AIソリューション展開",
                "9億ユーザーのさらなる有料化転換",
                "政府・防衛向けAIプラットフォーム需要の取り込み",
            ],
            "threats": [
                "Meta Llama・DeepSeekなどオープンソースによる価格圧力",
                "EU AI法・米国規制強化による開発・販売の制約",
                "営利化構造変更（非営利→PBC化）への規制当局の懸念",
                "Google・Anthropic・xAIからの競合激化",
            ],
        },
        "p4": {
            "product": "ChatGPT（コンシューマー・チームツール）とOpenAI APIの2本柱。GPT-5・o3推論・Sora動画・Operatorエージェントで幅広くカバー。カスタムGPT作成・Code Interpreter・音声モード対応。",
            "price": "Free / Plus $20/月 / Pro $200/月 / Business $30/ユーザー/月 / Enterprise ~$60/ユーザー/月（交渉制）。API: GPT-4o $2.50/百万トークン。エンタープライズ最小$108K/年〜数百万ドル規模。",
            "place": "直販エンタープライズセールス（~107名）・Bainパートナーシップ・Microsoft Azure Marketplace・ChatGPT.comセルフサーブ・開発者コミュニティ直接利用。",
            "promotion": "ChatGPTのPLG（製品主導成長）がメインエンジン。コンシューマー認知を企業導入に転換するボトムアップモーション。OpenAI DevDayカンファレンス・APIクレジット・開発者ドキュメント。",
        },
        "interview_tips": [
            "「なぜOpenAIか」→ ChatGPTブランドとPLGからエンタープライズ転換という独自の営業機会を語る",
            "競合理解: Claude=技術者向け、Gemini=Googleスタック依存、ChatGPT=ビジネスユーザーに最も親しみやすい",
            "最低150席・年間契約モデルなので、大口取引経験（Amazon Brandsでの大手クライアント対応）が活きる",
            "Bainパートナー経由のコンサル連携営業が増えており、ソリューション提案力を強調する",
        ],
    },
    "Anthropic": {
        "tagline": "安全性重視・エンタープライズ特化の急成長AIラボ",
        "snapshot": "ARR $19B・従業員~1,100名・評価額$380B・Series G $30B調達",
        "c3": {
            "company": [
                "コーディング（Claude Code $2.5B ARR）と200Kトークン長文脈処理で技術的差別化",
                "収益の80%以上がエンタープライズ顧客、500社以上が年間$1M超支出",
                "AWSとGoogleからの戦略的投資によりBedrock・Vertex AIが主要流通チャネル",
            ],
            "customer": [
                "大企業エンタープライズ: $100K〜$1M+/年の年間ライセンス契約が中心",
                "規制産業（金融・医療・法律）: Constitutional AIの安全性が調達基準に合う",
                "技術チーム: Claude Codeによるコーディング自動化・AIエージェント開発",
            ],
            "competitor": [
                "OpenAI（コンシューマーブランド）、Google（インフラ・クラウド統合）、Meta Llama（オープンソース）",
                "勝ちパターン: コーディング・安全性・長文脈処理でエンジニアリングチームの評価が高い",
                "負けパターン: コンシューマー認知でOpenAIに大差、AWS/GCP依存でクラウドマージン薄い",
            ],
        },
        "swot": {
            "strengths": [
                "Claude Codeが独自製品として急成長（$2.5B ARR）",
                "Constitutional AIによる安全性フレームワークで規制業界での差別化",
                "AWS・Googleからの投資とBedrockチャネルによる展開力",
                "エンタープライズ収益比率80%の強固なB2Bモデル",
            ],
            "weaknesses": [
                "コンシューマーブランド認知でOpenAI・Googleに大きく劣る",
                "クォータ持ち営業が~18名と極めて少なく商談対応に限界",
                "AWS・GCP両方への依存で自社クラウドマージンを確保できない",
                "GitHub Copilot・Cursorなどコーディング競合からの急速なプレッシャー",
            ],
            "opportunities": [
                "Claude Code/$2.5B ARRをさらに拡大しAIコーディング市場のデファクトへ",
                "$380B評価の資金力で営業・GTMチームを大幅拡充",
                "AWS Bedrockを通じた何十万社ものAWS顧客への展開加速",
                "医療・法律・金融の垂直特化モデルで規制業界を囲い込み",
            ],
            "threats": [
                "OpenAIとのコーディング市場での直接競合激化",
                "Meta Llama・DeepSeekなどオープンソースの価格破壊",
                "Opus 4.5で67%値下げなどトークン単価急落による収益圧迫",
                "Amazon・Googleがパートナーかつ競合という利益相反関係",
            ],
        },
        "p4": {
            "product": "Claude 3.5/3.7/4系モデル＋Claude Codeが主力。200Kトークン長文脈、コーディング・文書分析に特に強い。Constitutional AI安全性・コンピュータ操作（Computer Use）対応。",
            "price": "Free / Pro $20/月 / Team $30/ユーザー/月 / Enterprise 交渉制。API: Sonnet $3/百万トークン / Opus $5（67%値下げ後）。エンタープライズ$100K〜$1M+/年、500社が$1M超。",
            "place": "Claude.ai直販・Anthropic API直接契約・Amazon Bedrock（最大流通チャネル）・Google Cloud Vertex AI・Snowflake/Salesforce等ISVパートナー。",
            "promotion": "研究論文・ベンチマーク公開による開発者コミュニティの信頼構築。Constitutional AI研究の権威性がブランド。Bedrock経由のインバウンド→直販エンタープライズ交渉のモーション。",
        },
        "interview_tips": [
            "「なぜAnthropicか」→ 規制産業の大型エンタープライズへの長期パートナー営業、安全性とコーディングでOpenAIと差別化できると語る",
            "~18名のクォータ持ちで$19B ARRを支える→一人当たりの裁量が極めて大きい。「大きなテリトリーを自律的に開拓できる」姿勢をアピール",
            "AWS Bedrock経由が主チャネル→Amazon/AWS知識がある人材として即戦力をアピールできる",
            "Claude Codeの急成長（$2.5B ARR）を具体的に語れると、最もホットな製品を理解していることをアピールできる",
        ],
    },
    "Google DeepMind": {
        "tagline": "最大のインフラ・データ基盤を持つAIのフルスタックプレイヤー",
        "snapshot": "Google Cloud ARR $15.2B/Q（前年比+34%）・受注残高$240B・Alphabet時価総額$2T+",
        "c3": {
            "company": [
                "独自TPUインフラ＋Geminiモデル＋Vertex AI PaaSの垂直統合。AlphaFoldなど科学分野の先端研究",
                "Google Workspace 4,500万組織へのAI機能展開という圧倒的ディストリビューション",
                "Google Cloud Q4 2025で記録的$10億超規模の大型契約が複数成立",
            ],
            "customer": [
                "既存GCP顧客（既にGoogleインフラを使う大企業）へのクロスセルが最大の強み",
                "Google Workspace利用組織（4,500万）への生産性AI機能追加販売",
                "医薬・製造・小売など垂直業種エンタープライズ、政府機関（Google Public Sector）",
            ],
            "competitor": [
                "Microsoft Azure（OpenAI提携）、AWS（Anthropic提携）、OpenAI/Anthropic直販",
                "勝ちパターン: 既存GCP/Workspace顧客への追加販売、TPU価格優位、2Mトークン長文脈処理",
                "負けパターン: 組織の巨大さゆえの意思決定の遅さ、LLM単体ブランド認知でOpenAI/Anthropicに劣る",
            ],
        },
        "swot": {
            "strengths": [
                "世界最大規模のAIインフラ（TPU）と研究組織（DeepMind）の組み合わせ",
                "Google Workspace 4,500万組織へのAI展開という圧倒的ディストリビューション",
                "$240B受注残高が示す長期エンタープライズ契約の深さ",
                "Gemini 2.5の2Mトークンと低コストFlashモデルの価格競争力",
            ],
            "weaknesses": [
                "DeepMind・Google Brain・Google Cloud統合が不完全で製品戦略が不明確に見える",
                "Bard→Gemini等の度重なるリブランドが顧客の信頼を損ねるケースがある",
                "プライバシー・データ利用懸念が規制業界での採用を阻害",
                "AI純粋プレイヤーと比べてエンタープライズAI営業の特化度が低い",
            ],
            "opportunities": [
                "Google Cloud $240B受注残高を背景にしたAIエージェント・Workspace AIの大規模展開",
                "医薬・製造・小売の垂直特化AIソリューション（Vertex AI軸）",
                "Workspace AIユーザーへの追加AI機能課金による収益最大化",
                "A2Aプロトコル策定などAIエージェント標準化のリード",
            ],
            "threats": [
                "Microsoft Azure + OpenAIの連合体による強力なエンタープライズAIバンドル競合",
                "独禁法調査・EU規制強化によるビジネスリスク",
                "AI Overviewsの検索広告収益カニバリゼーション",
                "DeepMind研究者の離脱（Mistral・Inflection等）による研究競争力分散",
            ],
        },
        "p4": {
            "product": "Gemini LLM群＋Vertex AI MLOpsプラットフォーム＋Google Workspace AIの三本柱。2Mトークンコンテキスト、マルチモーダル（テキスト・画像・動画・音声・コード）、Agent Builder対応。",
            "price": "Gemini 2.5 Pro $1.25〜$2.50/百万トークン / Flash $0.30（最安値クラス）。Gemini for Workspace $30/ユーザー/月。大型ELA（Enterprise License Agreement）は$1M〜$10M+。",
            "place": "Google Cloud直販（GAE）・Cloud Marketplace・Workspaceリセラー（Accenture・Deloitte等SI）・Google Public Sector・API直接アクセス（AI Studio）。グローバル40リージョン以上。",
            "promotion": "Google Cloud Next年次カンファレンスを中心としたトップダウンマーケティング。CIOレベルEBR・既存クラウド拡大のランド＆エクスパンド。Google I/O・Free TierによるDeveloper吸引。",
        },
        "interview_tips": [
            "「なぜGoogle Cloudか」→ $240Bバックログと記録的大型案件増加のグロース機会、Workspaceとの統合による既存顧客への追加価値提案を語る",
            "「AIだけ」ではなく「AI＋インフラ＋Workspace」のバンドル全体の価値を提案するコンサルタティブスキルが必須",
            "Amazon Brand Specialist経験はAWS vs GCPの競合討議でリアルなインサイトを提供できる強みになる",
            "大型ELAの商談や複数部門を巻き込むCxOレベルの商談スキルを強調する",
        ],
    },
    "Mistral AI": {
        "tagline": "欧州発・オープンソース戦略でデータ主権と価格破壊を武器にするチャレンジャー",
        "snapshot": "ARR $400M・従業員~700名・評価額$12.7B・Series C調達$1.2B+",
        "c3": {
            "company": [
                "商用の20%という圧倒的低価格（Mistral Medium 3: $0.40/百万トークン）が最大の武器",
                "オープンウェイトモデル（商用利用可）でベンダーロックイン回避を訴求。開発者エコシステムを構築",
                "EU GDPR・データ主権コンプライアンスで欧州企業・政府機関の信頼を獲得",
            ],
            "customer": [
                "欧州大企業: データ主権要件でAWS・Azureを避けたい顧客。CMA CGMとの€100M規模パートナーシップ事例",
                "金融・公共・防衛: オンプレミスデプロイ要件が高い業種（Mistralのオンプレ対応が強み）",
                "コスト重視スタートアップ・開発者: 最安値クラスAPIと商用利用可オープンソースモデル",
            ],
            "competitor": [
                "OpenAI・Anthropic・Google（大手フロンティア）、Meta Llama（オープンソース競合）",
                "勝ちパターン: ①価格20% ②オープンウェイト ③欧州データ主権 ④オンプレ対応",
                "負けパターン: 最大規模フロンティアモデルの性能はGPT-5・Claude Opus・Gemini Ultraに劣る",
            ],
        },
        "swot": {
            "strengths": [
                "競合比20%の圧倒的低価格（Mistral Medium 3）",
                "オープンウェイトモデルによる開発者エコシステムとベンダーロックイン回避訴求",
                "欧州本社・EU規制適合による欧州大企業・政府からの強い信頼",
                "Ministral等の小型モデルでエッジ・オンデバイス市場もカバー",
            ],
            "weaknesses": [
                "~700人でOpenAI(4,500)・Google比で圧倒的に小規模、サポート力に限界",
                "最大規模フロンティアモデルの性能でGPT-5・Claude・Geminiに劣る",
                "北米市場でのブランド認知と直販チャネルが薄い（欧州偏重）",
                "API $400M ARRはまだ小規模でエンタープライズサポートへの投資余力が限られる",
            ],
            "opportunities": [
                "EU AI法・データ主権規制強化で欧州ローカルAI需要が急増",
                "Microsoft Azure提携拡大による北米展開加速",
                "Le ChatのコンシューマーARR拡大（$400M→$1B目標）",
                "オープンソースコミュニティ経由のボトムアップ企業採用",
            ],
            "threats": [
                "Meta Llama・DeepSeekとの直接競合（技術・コミュニティ規模で劣勢）",
                "Microsoft・Googleへのパートナー依存による独立性制約",
                "トークン価格の急落による収益圧迫（業界全体のコモディティ化）",
                "欧州規制との深い関係が地政学リスクにもなりうる",
            ],
        },
        "p4": {
            "product": "オープンウェイトと商用クローズドの両ラインナップ。Mistral Large / Medium（汎用）・Codestral（コーディング）・Ministral 3B/8B（エッジ）・Le Chat（チャットUI）。多言語（欧州言語）対応強。",
            "price": "Medium 3: $0.40/百万入力（業界最安値クラス） / Large: $2/百万入力 / Codestral: $0.30/百万入力。Le Chat Pro $14.99/月。エンタープライズオンプレデプロイ: $500K〜数百万ドルの長期ライセンス。",
            "place": "La Plateforme直販・Microsoft Azure AI Foundry・Google Cloud Vertex AI・AWS Bedrock（一部）・HuggingFace/GitHub（オープンソース）・欧州大企業・政府向けオンプレ直接ライセンス。",
            "promotion": "研究論文・ベンチマーク公開によるエンジニアコミュニティへの技術的権威付け。HuggingFaceでのオープンソース配布で開発者ベース構築。欧州大企業へのデータ主権・コスト削減・規制コンプライアンス訴求。",
        },
        "interview_tips": [
            "「なぜMistralか」→ 欧州データ主権規制の追い風・オープンソース戦略による独自ポジション、小チームで大きなインパクトを出せる環境を語る",
            "セールストーク: 「OpenAIより安くて欧州に安心なAI」。CFO・CISOへのコスト・セキュリティ訴求が多い",
            "小規模営業チームゆえに自律性と技術理解が必要。テクニカルとビジネスの両素養をアピール",
            "Amazon EC2・S3等のインフラ調達経験がオンプレデプロイの複雑な調達プロセス理解に活きると伝える",
        ],
    },
    "Scale AI": {
        "tagline": "AIデータファウンドリから政府・防衛向けAIプラットフォームへ進化中",
        "snapshot": "売上 $870M（2024年）→$2B+（2025年目標）・評価額$29B・Meta 49%株取得",
        "c3": {
            "company": [
                "高品質な学習データ生成・RLHF・モデル評価で業界最高水準の実績。DoD Donovanで政府市場を深耕",
                "Scale Donovan（政府・防衛向けAIエージェント）で$41M〜$100Mの長期DoD契約を獲得",
                "Meta 49%株取得後は従来の主要顧客（OpenAI・Google）が離脱中→転換期",
            ],
            "customer": [
                "AIラボ・BigTech（旧: OpenAI・Meta・Google等のモデルトレーニング用データ）※Meta投資後離脱が発生",
                "米国政府・防衛省（DoD/CDAO）: $100M規模の5年長期契約",
                "自動車・ロボティクス（GM・Ford等のコンピュータビジョン）・エンタープライズAI開発チーム",
            ],
            "competitor": [
                "Surge AI（OpenAI・Google離脱後の新データパートナーとして急成長）・Labelbox・Appen",
                "勝ちパターン: データ品質の高さ・Donovanによる政府市場の独自ポジション",
                "負けパターン: Meta 49%投資後にOpenAI・Googleが離脱→最大顧客セグメントで信頼失墜",
            ],
        },
        "swot": {
            "strengths": [
                "Donovanで$100M以上の長期DoD契約という政府・防衛市場の独自ポジション",
                "AIデータ品質評価・SEAL研究での業界権威性",
                "Metaの$14.8B投資による潤沢な資金力",
                "データラベリングからモデル評価・エンタープライズデプロイまでの一貫プラットフォーム",
            ],
            "weaknesses": [
                "Meta 49%投資後にOpenAI・Googleが離脱という最大の顧客信頼危機",
                "CEO Alexandr WangのMeta異動による創業者不在と組織的混乱",
                "データラベリングのコモディティ化（OpenAI等が内製化・オープンソース化を推進）",
                "人力アノテーション依存は自動化AIに長期的に代替されるリスク",
            ],
            "opportunities": [
                "政府・防衛市場の拡大（Donovan・Thunderforgeによる米国DoD深耕）",
                "Metaとのシナジーによる新製品・新市場開拓",
                "Scale Labs（2026年新設）によるAI安全性・評価の研究権威化",
                "エンタープライズAIエージェント評価・QA市場でのポジション確立",
            ],
            "threats": [
                "Surge AI等競合によるシェア奪取（Meta投資後の顧客離脱タイミングで加速）",
                "AIの自己学習・合成データ生成進化による人力データラベリング市場の縮小",
                "Meta 49%株式保有の利益相反が今後の顧客獲得にマイナスに働き続ける",
                "米国政府との深い関係が地政学的緊張でリスク要因になる可能性",
            ],
        },
        "p4": {
            "product": "Data Engine（データ収集・アノテーション）・GenAI Platform（モデル評価・ファインチューニング）・Donovan（政府向けAIエージェント）・SEAL（安全性評価）の4本柱。",
            "price": "データサービスはプロジェクトベース（$500K〜数百万ドル）・GenAI Platform年間ライセンス（$200K〜$2M/年）・Donovan DoD契約（$41M〜$100M、5年間）。API非公開・カスタム見積もり。",
            "place": "直販エンタープライズセールス・Scale Public Sector部門（OTA・GWACコントラクト）・政府・防衛SIパートナー・AWS/Azure等クラウドマーケットプレイス（一部）。米国中心。",
            "promotion": "SEALのベンチマーク・研究論文による技術的権威性とOpenAI・Meta等のロゴ実績でエンタープライズ信頼構築。CTO・Head of AI Engineering向け技術訴求、政府向けはDoD CDAO・防衛省調達担当への政策・セキュリティ訴求。",
        },
        "interview_tips": [
            "「なぜScale AIか」→ Meta投資後の転換期（データラベリング→エンタープライズAIプラットフォーム）を的確に理解し、変化の中で成長できる営業として自己を位置づける",
            "政府・防衛（Donovan）とエンタープライズ（GenAI Platform）の両セグメントで異なるセールスモーション。どちらにフォーカスするか面接前に明確にする",
            "Meta投資による顧客離脱への反論準備: 「政府市場とエンタープライズ評価市場は中立性を保てる」",
            "Amazonでの複雑なソリューション提案（Amazon Ads等）の経験がエンタープライズ直販営業に直結する",
        ],
    },
}


def _is_sales_job(job: Job) -> bool:
    text = f"{job.title} {job.department}".lower()
    return any(kw in text for kw in SALES_KEYWORDS)


def _is_match_job(job: Job) -> bool:
    """Amazon Brand Specialist経験とのマッチ度が高いポジション。"""
    text = f"{job.title} {job.department} {job.description}".lower()
    return any(kw in text for kw in MATCH_KEYWORDS)


def _company_profile_json(articles: list[Article], jobs: list[Job]) -> str:
    """各企業のSales分析データをJSON化する。"""
    profile_companies = ["OpenAI", "Anthropic", "Google DeepMind", "Mistral AI", "Scale AI"]
    profiles: dict = {}

    for company in profile_companies:
        company_jobs  = [j for j in jobs if j.company == company]
        sales_jobs    = [j for j in company_jobs if _is_sales_job(j)]

        # 部門内訳
        dept_counts: dict[str, int] = {}
        for j in sales_jobs:
            dept = j.department or "その他"
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        dept_sorted = sorted(dept_counts.items(), key=lambda x: -x[1])[:8]

        remote_count = sum(1 for j in sales_jobs if j.is_remote)

        # おすすめ度スコア（Sales求人数ベース）
        score = min(5, max(1, len(sales_jobs) // 3 + 1))

        # Sales求人一覧（Japan/Tokyo/Remote優先 → マッチ度 → 新着順）
        def _is_japan_job(j: Job) -> bool:
            loc = j.location.lower()
            return any(kw in loc for kw in ("japan", "tokyo", "日本", "東京"))

        def _sort_key(j: Job):
            japan_score = 3 if _is_japan_job(j) else (1 if j.is_remote else 0)
            match_score = 2 if _is_match_job(j) else 0
            date_score  = j.posted_date.timestamp() if j.posted_date else 0
            return (japan_score, match_score, date_score)

        sales_sorted = sorted(sales_jobs, key=_sort_key, reverse=True)[:40]

        # ニュース
        company_news = [a for a in articles if a.company == company]

        salary = SALARY_DATA.get(company, {})
        profiles[company] = {
            "color":          COMPANY_COLORS.get(company, "#6366f1"),
            "total_jobs":     len(company_jobs),
            "sales_count":    len(sales_jobs),
            "remote_count":   remote_count,
            "score":          score,
            "dept_breakdown": dict(dept_sorted),
            "salary":         salary,
            "sales_jobs": [
                {
                    "title":      j.title,
                    "department": j.department,
                    "location":   j.location,
                    "url":        j.url,
                    "posted":     j.posted_date.astimezone(JST).strftime("%Y-%m-%d")
                                  if j.posted_date else "",
                    "is_remote":  j.is_remote,
                    "description": j.description,
                    "is_match":   _is_match_job(j),
                    "is_japan":   _is_japan_job(j),
                }
                for j in sales_sorted
            ],
            "news": [
                {
                    "title":       a.title,
                    "url":         a.url,
                    "published":   a.published.astimezone(JST).strftime("%m/%d %H:%M"),
                    "topics":      a.topics,
                    "job_relevant": any(t in JOB_RELEVANT_TOPICS for t in a.topics),
                }
                for a in company_news[:6]
            ],
        }

    return json.dumps(profiles, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Data serialisation helpers
# ---------------------------------------------------------------------------
def _articles_to_json(articles: list[Article]) -> str:
    data = []
    for a in articles:
        data.append({
            "title":          a.title,
            "url":            a.url,
            "published":      a.published.astimezone(JST).strftime("%Y-%m-%d %H:%M"),
            "summary":        a.ai_summary,
            "source":         a.source_name,
            "category":       a.category,
            "company":        a.company,
            "topics":         a.topics,
            "job_relevant":   any(t in JOB_RELEVANT_TOPICS for t in a.topics),
            "priority_source": a.priority_source,
        })
    return json.dumps(data, ensure_ascii=False)


def _jobs_to_json(jobs: list[Job]) -> str:
    data = []
    for j in jobs:
        pub = ""
        if j.posted_date:
            try:
                pub = j.posted_date.astimezone(JST).strftime("%Y-%m-%d")
            except Exception:
                pub = str(j.posted_date)[:10]
        data.append({
            "title":      j.title,
            "company":    j.company,
            "location":   j.location,
            "department": j.department,
            "url":        j.url,
            "posted":     pub,
            "is_remote":  j.is_remote,
            "description": j.description,
        })
    return json.dumps(data, ensure_ascii=False)


def _all_topics(articles: list[Article]) -> list[str]:
    seen: dict[str, int] = {}
    for a in articles:
        for t in a.topics:
            seen[t] = seen.get(t, 0) + 1
    job  = [t for t in seen if t in JOB_RELEVANT_TOPICS]
    rest = sorted((t for t in seen if t not in JOB_RELEVANT_TOPICS), key=lambda t: -seen[t])
    return job + rest


def _article_companies(articles: list[Article]) -> list[str]:
    seen = []
    for a in articles:
        if a.company and a.company not in seen:
            seen.append(a.company)
    return seen


def _job_departments(jobs: list[Job]) -> dict[str, list[str]]:
    """Return {company: [dept, ...]} sorted by frequency."""
    from collections import defaultdict, Counter
    by_company: dict[str, Counter] = defaultdict(Counter)
    for j in jobs:
        if j.department:
            by_company[j.company][j.department] += 1
    return {c: [d for d, _ in counter.most_common()] for c, counter in by_company.items()}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def generate_dashboard(
    articles: list[Article],
    jobs: list[Job] | None = None,
    report_date: datetime | None = None,
) -> Path:
    if report_date is None:
        report_date = datetime.now(tz=JST)
    if jobs is None:
        jobs = []

    date_str     = report_date.strftime("%Y-%m-%d")
    output_dir   = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path  = output_dir / f"{date_str}_dashboard.html"

    # Stats
    total        = len(articles)
    job_rel_count = sum(1 for a in articles if any(t in JOB_RELEVANT_TOPICS for t in a.topics))
    priority_articles = [a for a in articles if a.priority_source]
    priority_count = len(priority_articles)
    cat_counts   = {k: sum(1 for a in articles if a.category == k) for k in CATEGORY_LABELS}
    topics       = _all_topics(articles)
    art_companies = _article_companies(articles)
    job_depts    = _job_departments(jobs)
    job_companies = list(dict.fromkeys(j.company for j in jobs))

    priority_source_info = {
        "Bloomberg Technology":      "米国最大級の経済・金融メディア。AI企業の資金調達・M&A・株式市場への影響を速報する。",
        "Financial Times Technology": "英国発の世界的経済紙。AI規制・欧州市場・グローバルテック企業の戦略分析に強い。",
        "TechCrunch AI":             "シリコンバレー発のスタートアップ専門メディア。AI新興企業の資金調達・プロダクト発表を最速で報じる。",
    }
    priority_source_info_js = json.dumps(priority_source_info, ensure_ascii=False)

    articles_json          = _articles_to_json(articles)
    priority_articles_json = _articles_to_json(priority_articles)
    jobs_json              = _jobs_to_json(jobs)
    profiles_json          = _company_profile_json(articles, jobs)
    amazon_comp_js         = json.dumps(AMAZON_COMP, ensure_ascii=False)
    salary_jp_js           = json.dumps(SALARY_DATA_JP, ensure_ascii=False)
    amazon_comp_jp_js      = json.dumps(AMAZON_COMP_JP, ensure_ascii=False)
    japan_benchmark_js     = json.dumps(JAPAN_BENCHMARK, ensure_ascii=False)
    company_analysis_js    = json.dumps(COMPANY_ANALYSIS, ensure_ascii=False)
    generated_at           = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M JST")

    company_colors_js = json.dumps(COMPANY_COLORS)
    job_topics_js = json.dumps(list(JOB_RELEVANT_TOPICS), ensure_ascii=False)

    # Build department filter buttons per company
    dept_buttons = ""
    for company in job_companies:
        depts = job_depts.get(company, [])[:12]  # top 12 depts
        color = COMPANY_COLORS.get(company, "#6366f1")
        dept_buttons += f'<div class="dept-group" data-dept-company="{company}" style="display:none">'
        dept_buttons += f'<span class="filter-label">部門:</span>'
        dept_buttons += f'<button class="btn active dept-all-btn" data-dept="all" style="--c:{color}">すべて</button>'
        for d in depts:
            dept_buttons += f'<button class="btn dept-btn" data-dept="{d}" style="--c:{color}">{d}</button>'
        dept_buttons += '</div>'

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI News Dashboard — {date_str}</title>
<style>
:root {{
  --bg:#0f172a; --surface:#1e293b; --surface2:#334155;
  --border:#475569; --text:#f1f5f9; --muted:#94a3b8;
  --indigo:#6366f1; --sky:#0ea5e9; --emerald:#10b981;
  --amber:#f59e0b; --red:#ef4444; --violet:#7c3aed; --gold:#fbbf24;
  --openai:#10a37f; --anthropic:#c96442; --deepmind:#4285f4; --google:#34a853;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.6}}

/* ── Header ── */
header{{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 24px;position:sticky;top:0;z-index:200}}
.header-inner{{max-width:1400px;margin:0 auto;display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
header h1{{font-size:17px;font-weight:700;white-space:nowrap}}
header h1 span{{color:var(--muted);font-weight:400;font-size:12px;margin-left:8px}}
#search{{flex:1;min-width:180px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:6px 12px;color:var(--text);font-size:13px;outline:none}}
#search:focus{{border-color:var(--indigo)}}

/* ── Tabs ── */
.tabs{{display:flex;gap:2px;background:var(--bg);border-radius:8px;padding:3px;border:1px solid var(--border)}}
.tab-btn{{padding:5px 18px;border-radius:6px;border:none;background:transparent;color:var(--muted);font-size:13px;cursor:pointer;transition:all .15s;white-space:nowrap}}
.tab-btn.active{{background:var(--surface);color:var(--text);font-weight:600}}

/* ── Stats ── */
.stats{{max-width:1400px;margin:14px auto;padding:0 24px;display:flex;gap:10px;flex-wrap:wrap}}
.stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 18px;flex:1;min-width:110px}}
.stat-card .num{{font-size:26px;font-weight:800}}
.stat-card .label{{color:var(--muted);font-size:11px;margin-top:1px}}
.stat-card.s-job .num{{color:var(--gold)}}
.stat-card.s-openai .num{{color:var(--openai)}}
.stat-card.s-anthropic .num{{color:var(--anthropic)}}
.stat-card.s-deepmind .num{{color:var(--deepmind)}}

/* ── Filter bar ── */
.filter-bar{{max-width:1400px;margin:0 auto 14px;padding:0 24px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}}
.filter-label{{color:var(--muted);font-size:11px;margin-right:2px}}
.btn{{border:1px solid var(--border);background:var(--surface);color:var(--muted);border-radius:20px;padding:4px 12px;font-size:12px;cursor:pointer;transition:all .15s;white-space:nowrap}}
.btn:hover{{background:var(--surface2);color:var(--text)}}
.btn.active{{background:var(--indigo);border-color:transparent;color:#fff}}
.btn[data-cat="all"].active{{background:var(--surface2);color:var(--text)}}
.btn[data-cat="target_company"].active{{background:var(--indigo)}}
.btn[data-cat="overseas"].active{{background:var(--sky)}}
.btn[data-cat="japan"].active{{background:var(--emerald)}}
.btn[data-cat="job"].active{{background:var(--gold);color:#000}}
.dept-btn.active,.dept-all-btn.active{{background:var(--c,var(--indigo));border-color:transparent;color:#fff}}
.topic-btn{{padding:3px 9px;font-size:11px}}
.topic-btn.active{{background:var(--violet);border-color:transparent;color:#fff}}
.sep{{width:1px;height:18px;background:var(--border);margin:0 2px}}
.company-filter-btn{{font-weight:600}}
.company-filter-btn[data-company="OpenAI"].active{{background:var(--openai)}}
.company-filter-btn[data-company="Anthropic"].active{{background:var(--anthropic)}}
.company-filter-btn[data-company="Google DeepMind"].active{{background:var(--deepmind)}}
.company-filter-btn[data-company="Google"].active{{background:var(--google)}}

/* ── Grid ── */
.grid{{max-width:1400px;margin:0 auto;padding:0 24px 40px;display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}}

/* ── Article card ── */
.card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:7px;transition:transform .15s,box-shadow .15s;position:relative;overflow:hidden}}
.card:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.4)}}
.card.job-relevant{{border-color:var(--gold)}}
.card.job-relevant::before{{content:'⭐ 転職関連';position:absolute;top:0;right:0;background:var(--gold);color:#000;font-size:10px;font-weight:700;padding:2px 9px;border-bottom-left-radius:8px}}
.cat-bar{{height:3px;border-radius:2px;margin:-14px -14px 7px}}
.cat-bar.target_company{{background:var(--indigo)}}
.cat-bar.overseas{{background:var(--sky)}}
.cat-bar.japan{{background:var(--emerald)}}
.card-meta{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.source-badge{{font-size:11px;color:var(--muted);background:var(--surface2);border-radius:5px;padding:2px 7px;white-space:nowrap}}
.company-badge{{font-size:11px;font-weight:700;border-radius:5px;padding:2px 7px;color:#fff;white-space:nowrap}}
.pub-time{{font-size:11px;color:var(--muted);margin-left:auto;white-space:nowrap}}
.card-title{{font-size:13px;font-weight:600;line-height:1.4}}
.card-title a{{color:var(--text);text-decoration:none}}
.card-title a:hover{{color:var(--sky)}}
.card-summary{{font-size:12px;color:var(--muted);line-height:1.6;flex:1}}
.topics{{display:flex;gap:4px;flex-wrap:wrap;margin-top:auto}}
.topic-tag{{font-size:11px;border-radius:10px;padding:2px 7px;background:var(--surface2);color:var(--muted);border:1px solid var(--border)}}
.topic-tag.hiring{{background:#4a1d96;color:#ddd6fe;border-color:var(--violet)}}
.topic-tag.product{{background:#7f1d1d;color:#fca5a5;border-color:#dc2626}}
.topic-tag.funding{{background:#78350f;color:#fde68a;border-color:#d97706}}
.topic-tag.reorg{{background:#164e63;color:#a5f3fc;border-color:#0891b2}}

/* ── Priority banner ── */
.priority-section{{max-width:1400px;margin:0 auto 18px;padding:0 24px}}
.priority-header{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.priority-header h2{{font-size:15px;font-weight:700;color:#fbbf24}}
.priority-header .priority-count{{background:#78350f;color:#fde68a;border-radius:12px;padding:2px 9px;font-size:11px;font-weight:700}}
.priority-source-pills{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.priority-source-pill{{background:#1c1206;border:1px solid #92400e;border-radius:8px;padding:6px 12px;display:flex;flex-direction:column;gap:2px}}
.priority-source-pill .ps-name{{font-size:12px;font-weight:700;color:#fbbf24}}
.priority-source-pill .ps-desc{{font-size:11px;color:var(--muted);line-height:1.5}}
.priority-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}}
.priority-card{{background:linear-gradient(135deg,#1c1206 0%,#1e293b 100%);border:1px solid #92400e;border-radius:10px;padding:12px;display:flex;flex-direction:column;gap:6px;position:relative;transition:transform .15s,box-shadow .15s}}
.priority-card:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(251,191,36,.15)}}
.priority-card .fire-bar{{height:2px;border-radius:1px;margin:-12px -12px 8px;background:linear-gradient(90deg,#f59e0b,#ef4444,#f59e0b)}}
.priority-card .p-meta{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.priority-card .p-source{{font-size:11px;font-weight:700;color:#fbbf24;background:#451a03;border-radius:4px;padding:2px 7px}}
.priority-card .p-time{{font-size:11px;color:var(--muted);margin-left:auto}}
.priority-card .p-title{{font-size:13px;font-weight:600;line-height:1.4}}
.priority-card .p-title a{{color:var(--text);text-decoration:none}}
.priority-card .p-title a:hover{{color:#fbbf24}}
.priority-card .p-summary{{font-size:12px;color:var(--muted);line-height:1.6}}
.priority-card .p-topics{{display:flex;gap:4px;flex-wrap:wrap}}
.priority-card.job-relevant{{border-color:#d97706}}
.priority-card.job-relevant::before{{content:'⭐ 転職関連';position:absolute;top:0;right:0;background:var(--gold);color:#000;font-size:10px;font-weight:700;padding:2px 9px;border-bottom-left-radius:8px}}

/* ── Job card ── */
.job-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:8px;transition:transform .15s,box-shadow .15s}}
.job-card:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.4)}}
.job-company-bar{{height:3px;border-radius:2px;margin:-14px -14px 7px}}
.job-company-bar.OpenAI{{background:var(--openai)}}
.job-company-bar.Anthropic{{background:var(--anthropic)}}
.job-company-bar.Google.DeepMind{{background:var(--deepmind)}}
.job-company-bar.Google{{background:var(--google)}}
.job-meta{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.job-company-badge{{font-size:11px;font-weight:700;border-radius:5px;padding:2px 8px;color:#fff}}
.job-company-badge.OpenAI{{background:var(--openai)}}
.job-company-badge.Anthropic{{background:var(--anthropic)}}
.job-company-badge.Google-DeepMind{{background:var(--deepmind)}}
.job-company-badge.Google{{background:var(--google)}}
.job-dept{{font-size:11px;color:var(--muted);background:var(--surface2);border-radius:5px;padding:2px 7px}}
.job-date{{font-size:11px;color:var(--muted);margin-left:auto;white-space:nowrap}}
.job-title{{font-size:13px;font-weight:600;line-height:1.4}}
.job-title a{{color:var(--text);text-decoration:none}}
.job-title a:hover{{color:var(--sky)}}
.job-location{{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:4px}}
.remote-badge{{font-size:10px;background:#064e3b;color:#6ee7b7;border:1px solid #10b981;border-radius:8px;padding:1px 7px}}
.job-desc{{font-size:12px;color:var(--muted);line-height:1.6}}
.apply-btn{{display:inline-block;background:var(--indigo);color:#fff;border-radius:7px;padding:6px 14px;font-size:12px;font-weight:600;text-decoration:none;text-align:center;margin-top:auto;transition:background .15s}}
.apply-btn:hover{{background:#4f46e5}}

/* ── 企業カルテ tab ── */
.profile-nav{{max-width:1400px;margin:14px auto 0;padding:0 24px;display:flex;gap:8px;flex-wrap:wrap}}
.profile-nav-btn{{padding:7px 18px;border-radius:8px;border:2px solid var(--border);background:var(--surface);color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;transition:all .15s}}
.profile-nav-btn.active{{color:#fff;border-color:transparent}}
.profile-panel{{max-width:1400px;margin:14px auto 40px;padding:0 24px;display:none}}
.profile-panel.active{{display:block}}
.profile-header{{display:flex;align-items:center;gap:12px;margin-bottom:16px;padding:16px 20px;border-radius:12px;border:1px solid var(--border);background:var(--surface)}}
.profile-header .co-dot{{width:14px;height:14px;border-radius:50%;flex-shrink:0}}
.profile-header h2{{font-size:18px;font-weight:800;flex:1}}
.profile-header .score{{display:flex;gap:3px;font-size:18px}}
.profile-stats-row{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:16px}}
.ps-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 16px}}
.ps-card .num{{font-size:24px;font-weight:800}}
.ps-card .lbl{{font-size:11px;color:var(--muted);margin-top:2px}}
.profile-body{{display:grid;grid-template-columns:300px 1fr;gap:16px;align-items:start}}
@media(max-width:780px){{.profile-body{{grid-template-columns:1fr}}}}
.dept-chart-box{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}}
.dept-chart-box h3{{font-size:13px;font-weight:700;margin-bottom:12px;color:var(--muted)}}
.dept-bar-row{{margin-bottom:9px}}
.dept-bar-label{{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:3px}}
.dept-bar-track{{background:var(--surface2);border-radius:3px;height:6px}}
.dept-bar-fill{{height:6px;border-radius:3px;transition:width .4s}}
.remote-stat{{margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}}
.remote-stat .label{{font-size:11px;color:var(--muted);margin-bottom:6px}}
.remote-bar{{background:var(--surface2);border-radius:4px;height:10px}}
.remote-bar-fill{{height:10px;border-radius:4px;background:var(--emerald)}}
.match-box{{margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}}
.match-box h4{{font-size:11px;color:var(--muted);margin-bottom:6px}}
.match-tip{{font-size:11px;color:#6ee7b7;background:#064e3b;border-radius:6px;padding:4px 8px;display:inline-block;margin:2px 2px}}
.sales-list-box{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}}
.sales-list-box h3{{font-size:13px;font-weight:700;margin-bottom:12px;color:var(--muted)}}
.sales-job-item{{border-bottom:1px solid var(--border);padding:10px 0;display:flex;flex-direction:column;gap:4px}}
.sales-job-item:last-child{{border-bottom:none}}
.sales-job-item.is-match{{background:linear-gradient(90deg,rgba(16,185,129,.07) 0%,transparent 100%);border-radius:8px;padding:10px 8px;margin:-0 -8px}}
.sj-title-row{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.sj-match-badge{{font-size:10px;background:#064e3b;color:#6ee7b7;border:1px solid #10b981;border-radius:8px;padding:1px 7px;white-space:nowrap;flex-shrink:0}}
.sj-title{{font-size:13px;font-weight:600}}
.sj-title a{{color:var(--text);text-decoration:none}}
.sj-title a:hover{{color:var(--sky)}}
.sj-meta{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.sj-dept{{font-size:11px;color:var(--muted);background:var(--surface2);border-radius:4px;padding:1px 6px}}
.sj-loc{{font-size:11px;color:var(--muted)}}
.sj-date{{font-size:11px;color:var(--muted);margin-left:auto}}
.profile-news-box{{margin-top:16px;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}}
.profile-news-box h3{{font-size:13px;font-weight:700;margin-bottom:10px;color:var(--muted)}}
.news-item{{padding:8px 0;border-bottom:1px solid var(--border);display:flex;flex-direction:column;gap:3px}}
.news-item:last-child{{border-bottom:none}}
.news-item a{{font-size:13px;font-weight:600;color:var(--text);text-decoration:none}}
.news-item a:hover{{color:var(--sky)}}
.news-item-meta{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.news-item-time{{font-size:11px;color:var(--muted)}}
.news-item-tag{{font-size:10px;border-radius:8px;padding:1px 7px;background:var(--surface2);color:var(--muted)}}
.news-item-tag.job{{background:#4a1d96;color:#ddd6fe}}

/* ── 略語ツールチップ ── */
.abbr-term{{border-bottom:1px dashed var(--muted);cursor:help;position:relative;white-space:nowrap}}
.abbr-term::after{{content:attr(data-tip);position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:#1e293b;border:1px solid var(--border);color:var(--text);font-size:11px;white-space:nowrap;padding:4px 10px;border-radius:6px;pointer-events:none;opacity:0;transition:opacity .15s;z-index:999;font-weight:400;font-style:normal}}
.abbr-term:hover::after{{opacity:1}}
.glossary-bar{{max-width:1400px;margin:0 auto 10px;padding:0 24px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}}
.glossary-bar .gl-label{{font-size:11px;color:var(--muted);margin-right:4px}}
.gl-tag{{font-size:11px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:2px 8px;color:var(--muted)}}
.gl-tag b{{color:var(--text)}}

/* ── 年収セクション ── */
.salary-section{{margin-top:16px}}
.salary-section h3{{font-size:13px;font-weight:700;margin-bottom:10px;color:var(--muted)}}
.salary-meta{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;align-items:center}}
.quota-badge{{font-size:12px;font-weight:700;border-radius:8px;padding:3px 10px}}
.quota-badge.good{{background:#064e3b;color:#6ee7b7;border:1px solid #10b981}}
.quota-badge.warn{{background:#78350f;color:#fde68a;border:1px solid #d97706}}
.quota-badge.bad{{background:#7f1d1d;color:#fca5a5;border:1px solid #dc2626}}
.salary-links{{display:flex;gap:6px;flex-wrap:wrap}}
.salary-link{{font-size:11px;border-radius:6px;padding:3px 10px;border:1px solid var(--border);color:var(--muted);text-decoration:none;background:var(--surface2)}}
.salary-link:hover{{color:var(--sky)}}
.advice-box{{background:#0f172a;border-left:3px solid var(--amber);border-radius:0 8px 8px 0;padding:8px 12px;margin-bottom:12px;font-size:12px;line-height:1.7;color:var(--muted)}}
.advice-box.warn{{border-color:#ef4444}}
.salary-roles{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}}
.salary-role-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px}}
.salary-role-card .role-name{{font-size:11px;font-weight:700;color:var(--muted);margin-bottom:6px}}
.salary-role-card .ote-val{{font-size:20px;font-weight:800;color:#fbbf24}}
.salary-role-card .base-val{{font-size:11px;color:var(--muted);margin-top:2px}}
.salary-role-card .role-note{{font-size:10px;color:var(--muted);margin-top:4px;font-style:italic}}
.amazon-compare{{background:var(--surface2);border-radius:8px;padding:8px 12px;font-size:11px;color:var(--muted);margin-top:8px}}
.amazon-compare span{{color:var(--text);font-weight:700}}
.match-stars{{font-size:13px}}
.us-disclaimer{{background:#1e1a0a;border:1px solid #92400e;border-radius:8px;padding:8px 12px;font-size:11px;color:#fde68a;margin-bottom:10px;line-height:1.7}}
.us-disclaimer strong{{color:#fbbf24}}
.salary-tab-row{{display:flex;gap:0;margin-bottom:12px;border-radius:8px;overflow:hidden;border:1px solid var(--border);width:fit-content}}
.salary-tab{{padding:5px 16px;font-size:12px;font-weight:600;border:none;background:var(--surface);color:var(--muted);cursor:pointer;transition:all .15s}}
.salary-tab.active{{background:var(--indigo);color:#fff}}
.salary-panel{{display:none}}.salary-panel.active{{display:block}}
.jp-office-status{{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:12px}}
.jp-status-badge{{border-radius:6px;padding:2px 9px;font-size:11px;font-weight:700}}
.jp-status-badge.active{{background:#064e3b;color:#6ee7b7;border:1px solid #10b981}}
.jp-status-badge.hiring{{background:#1e3a5f;color:#93c5fd;border:1px solid #3b82f6;animation:pulse-border 2s infinite}}
.jp-status-badge.none{{background:#1f2937;color:var(--muted);border:1px solid var(--border)}}
@keyframes pulse-border{{0%,100%{{border-color:#3b82f6}}50%{{border-color:#93c5fd}}}}
.benchmark-table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}}
.benchmark-table th{{text-align:left;color:var(--muted);font-size:10px;padding:4px 8px;border-bottom:1px solid var(--border)}}
.benchmark-table td{{padding:5px 8px;border-bottom:1px solid rgba(71,85,105,.3)}}
.benchmark-table tr:last-child td{{border-bottom:none}}

/* ── 企業分析（3C/SWOT/4P）── */
.analysis-section{{margin-top:16px}}
.analysis-section h3{{font-size:13px;font-weight:700;margin-bottom:10px;color:var(--muted)}}
.analysis-tab-row{{display:flex;gap:0;margin-bottom:14px;border-radius:8px;overflow:hidden;border:1px solid var(--border);width:fit-content}}
.analysis-tab{{padding:5px 14px;font-size:12px;font-weight:600;border:none;background:var(--surface);color:var(--muted);cursor:pointer;transition:all .15s}}
.analysis-tab.active{{background:var(--violet);color:#fff}}
.analysis-panel{{display:none}}.analysis-panel.active{{display:block}}
.c3-tab-row{{display:flex;gap:0;margin-bottom:10px;border-radius:8px;overflow:hidden;border:1px solid var(--border);width:fit-content}}
.c3-tab{{padding:5px 16px;font-size:12px;font-weight:600;border:none;background:var(--surface);color:var(--muted);cursor:pointer;transition:all .15s}}
.c3-tab.active{{background:var(--violet);color:#fff}}
.c3-panel{{display:none}}.c3-panel.active{{display:block}}
.c3-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px}}
.c3-card ul{{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}}
.c3-card li{{font-size:12px;color:var(--muted);line-height:1.6;padding-left:14px;position:relative}}
.c3-card li::before{{content:"▸";position:absolute;left:0;color:var(--violet)}}
.swot-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.swot-card{{border-radius:10px;padding:14px}}
.swot-card.s{{background:#0a2318;border:1px solid #10b981}}.swot-card.s h4{{color:#6ee7b7}}
.swot-card.w{{background:#1f1315;border:1px solid #ef4444}}.swot-card.w h4{{color:#fca5a5}}
.swot-card.o{{background:#0f1e33;border:1px solid #3b82f6}}.swot-card.o h4{{color:#93c5fd}}
.swot-card.t{{background:#1c1506;border:1px solid #f59e0b}}.swot-card.t h4{{color:#fde68a}}
.swot-card h4{{font-size:12px;font-weight:700;margin-bottom:8px}}
.swot-card ul{{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:6px}}
.swot-card li{{font-size:12px;color:var(--muted);line-height:1.6;padding-left:12px;position:relative}}
.swot-card li::before{{content:"•";position:absolute;left:0}}
.p4-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
@media(max-width:700px){{.p4-grid{{grid-template-columns:1fr}}}}
.p4-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px}}
.p4-card h4{{font-size:12px;font-weight:700;margin-bottom:6px;color:var(--sky)}}
.p4-card p{{font-size:12px;color:var(--muted);line-height:1.7}}
.tips-list{{display:flex;flex-direction:column;gap:8px}}
.tip-item{{background:var(--surface);border-left:3px solid var(--violet);border-radius:0 8px 8px 0;padding:10px 14px;font-size:12px;color:var(--muted);line-height:1.7}}
.tip-num{{font-weight:700;color:var(--violet);margin-right:6px}}
.snapshot-bar{{background:var(--surface2);border-radius:8px;padding:8px 14px;font-size:11px;color:var(--muted);margin-bottom:12px}}

/* ── Google link card ── */
.google-link-card{{background:var(--surface);border:2px dashed var(--border);border-radius:12px;padding:20px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;text-align:center;grid-column:span 1}}
.google-link-card .google-logo{{font-size:32px}}
.google-link-card p{{color:var(--muted);font-size:12px}}
.google-link-btn{{display:inline-block;background:var(--google);color:#fff;border-radius:7px;padding:8px 18px;font-size:13px;font-weight:600;text-decoration:none;margin-top:4px}}

/* ── Empty state ── */
.empty{{display:none;grid-column:1/-1;text-align:center;padding:60px;color:var(--muted)}}
.empty .icon{{font-size:48px}}

/* ── Responsive ── */
@media(max-width:600px){{
  .grid{{grid-template-columns:1fr;padding:0 12px 32px}}
  .stats,.filter-bar{{padding:0 12px}}
  header{{padding:10px 12px}}
  .header-inner{{gap:8px}}
}}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <h1>🤖 AI News Dashboard <span>{date_str} &nbsp;|&nbsp; {generated_at}</span></h1>
    <div class="tabs" id="tabs">
      <button class="tab-btn active" data-tab="news">📰 ニュース</button>
      <button class="tab-btn" data-tab="jobs">💼 求人情報</button>
      <button class="tab-btn" data-tab="profile">🏢 企業カルテ</button>
    </div>
    <input id="search" type="text" placeholder="🔍 検索...">
  </div>
</header>

<!-- ══════════════ NEWS TAB ══════════════ -->
<div id="tab-news">
  <div class="stats">
    <div class="stat-card"><div class="num">{total}</div><div class="label">総記事数</div></div>
    <div class="stat-card s-job"><div class="num">{job_rel_count}</div><div class="label">💼 転職関連</div></div>
    <div class="stat-card" style="border-color:#f59e0b"><div class="num" style="color:#f59e0b">{priority_count}</div><div class="label">🔥 注目ソース</div></div>
    <div class="stat-card" style="border-color:var(--indigo)"><div class="num" style="color:var(--indigo)">{cat_counts.get("target_company",0)}</div><div class="label">🎯 ターゲット企業</div></div>
    <div class="stat-card" style="border-color:var(--sky)"><div class="num" style="color:var(--sky)">{cat_counts.get("overseas",0)}</div><div class="label">🌐 AI業界ニュース</div></div>
    <div class="stat-card" style="border-color:var(--emerald)"><div class="num" style="color:var(--emerald)">{cat_counts.get("japan",0)}</div><div class="label">🇯🇵 日本語</div></div>
  </div>

  <!-- 🔥 Priority sources banner -->
  <div class="priority-section" id="priority-section" style="{'display:none' if priority_count == 0 else ''}">
    <div class="priority-header">
      <h2>🔥 注目ソース速報</h2>
      <span class="priority-count">{priority_count}件</span>
    </div>
    <div class="priority-source-pills" id="priority-source-pills"></div>
    <div class="priority-grid" id="priority-grid"></div>
  </div>

  <div class="filter-bar" id="news-filters">
    <span class="filter-label">カテゴリ:</span>
    <button class="btn active" data-cat="all">すべて</button>
    <button class="btn" data-cat="target_company">🎯 ターゲット企業</button>
    <button class="btn" data-cat="overseas">🌐 業界ニュース</button>
    <button class="btn" data-cat="japan">🇯🇵 日本語</button>
    <button class="btn" data-cat="job">⭐ 転職関連</button>
    <button class="btn" data-cat="priority">🔥 注目ソース</button>
    {"".join(f'<button class="btn company-filter-btn" data-company="{c}">{c}</button>' for c in art_companies) if art_companies else ""}
    <div class="sep"></div>
    <span class="filter-label">トピック:</span>
    {"".join(f'<button class="btn topic-btn" data-topic="{t}">{t}</button>' for t in topics)}
  </div>
  <div class="grid" id="news-grid"></div>
</div>

<!-- ══════════════ JOBS TAB ══════════════ -->
<div id="tab-jobs" style="display:none">
  <div class="stats" id="job-stats"></div>
  <div class="filter-bar" id="job-filters">
    <span class="filter-label">企業:</span>
    <button class="btn active company-filter-btn" data-jcompany="all">すべて</button>
    {"".join(f'<button class="btn company-filter-btn" data-jcompany="{c}">{c}</button>' for c in job_companies)}
    <div class="sep"></div>
    <button class="btn" data-jlocation="japan">🇯🇵 日本・東京</button>
    <button class="btn" data-remote="true">🏠 リモート</button>
    <div class="sep"></div>
    {dept_buttons}
  </div>
  <div class="grid" id="jobs-grid"></div>
</div>

<!-- ══════════════ PROFILE TAB ══════════════ -->
<div id="tab-profile" style="display:none">
  <div class="glossary-bar">
    <span class="gl-label">📖 用語:</span>
    <span class="gl-tag"><b>AE</b> = Account Executive（顧客担当営業）</span>
    <span class="gl-tag"><b>BDR</b> = Business Development Rep（新規開拓営業）</span>
    <span class="gl-tag"><b>SDR</b> = Sales Development Rep（インバウンドリード対応）</span>
    <span class="gl-tag"><b>CSM</b> = Customer Success Manager（契約後の顧客支援）</span>
    <span class="gl-tag"><b>OTE</b> = On-Target Earnings（目標達成時の基本給＋コミッション合計）</span>
    <span class="gl-tag"><b>GTM</b> = Go-To-Market（市場進出戦略）</span>
    <span class="gl-tag"><b>クォータ</b> = 担当者ごとの売上目標額</span>
  </div>
  <div class="profile-nav" id="profile-nav"></div>
  <div id="profile-panels"></div>
</div>

<script>
const ARTICLES          = {articles_json};
const PRIORITY_ARTICLES   = {priority_articles_json};
const PRIORITY_SOURCE_INFO = {priority_source_info_js};
const JOBS              = {jobs_json};
const JOB_TOPICS        = new Set({job_topics_js});
const CO_COLORS         = {company_colors_js};

// ── Priority source pills ──
(function() {{
  const pills = document.getElementById("priority-source-pills");
  if (!pills) return;
  pills.innerHTML = Object.entries(PRIORITY_SOURCE_INFO).map(([name, desc]) =>
    `<div class="priority-source-pill">
      <span class="ps-name">${{name}}</span>
      <span class="ps-desc">${{desc}}</span>
    </div>`
  ).join("");
}})();

// ── Priority cards ──
(function() {{
  const grid = document.getElementById("priority-grid");
  if (!grid || PRIORITY_ARTICLES.length === 0) return;
  grid.innerHTML = PRIORITY_ARTICLES.map(a => {{
    const jobRel = a.job_relevant ? "job-relevant" : "";
    const summary = a.summary ? `<div class="p-summary">${{a.summary.replace(/\\n/g,"<br>")}}</div>` : "";
    const topics = a.topics.length ? `<div class="p-topics">${{a.topics.map(t=>`<span class="topic-tag">${{t}}</span>`).join("")}}</div>` : "";
    return `<div class="priority-card ${{jobRel}}">
      <div class="fire-bar"></div>
      <div class="p-meta"><span class="p-source">${{a.source}}</span><span class="p-time">${{a.published}}</span></div>
      <div class="p-title"><a href="${{a.url}}" target="_blank">${{a.title}}</a></div>
      ${{summary}}${{topics}}
    </div>`;
  }}).join("");
}})();

const TOPIC_CLS = {{"採用・人事":"hiring","新プロダクト":"product","資金調達":"funding","組織変更":"reorg"}};

// ── Tab switching ──
let currentTab = "news";
document.getElementById("tabs").addEventListener("click", e => {{
  const btn = e.target.closest(".tab-btn");
  if (!btn) return;
  currentTab = btn.dataset.tab;
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b===btn));
  document.getElementById("tab-news").style.display    = currentTab==="news"    ? "" : "none";
  document.getElementById("tab-jobs").style.display    = currentTab==="jobs"    ? "" : "none";
  document.getElementById("tab-profile").style.display = currentTab==="profile" ? "" : "none";
  document.getElementById("search").placeholder = currentTab==="news" ? "🔍 記事を検索..." : currentTab==="jobs" ? "🔍 求人を検索..." : "🔍 ポジションを検索...";
  applyFilters();
}});

// ── Search ──
document.getElementById("search").addEventListener("input", e => {{
  searchQuery = e.target.value.toLowerCase().trim();
  applyFilters();
}});

// ══════════════ NEWS LOGIC ══════════════
let activeCat = "all", activeCompany = null, activeTopics = new Set(), searchQuery = "";

function topicTag(t) {{
  const cls = JOB_TOPICS.has(t) ? (TOPIC_CLS[t] || "hiring") : "";
  return `<span class="topic-tag ${{cls}}">${{t}}</span>`;
}}

function renderArticle(a) {{
  const co = CO_COLORS[a.company] || "#6366f1";
  const companyBadge = a.company
    ? `<span class="company-badge" style="background:${{co}}">${{a.company}}</span>` : "";
  const summary = a.summary
    ? `<div class="card-summary">${{a.summary.replace(/\\n/g,"<br>")}}</div>` : "";
  const topics = a.topics.length
    ? `<div class="topics">${{a.topics.map(topicTag).join("")}}</div>` : "";
  return `<div class="card ${{a.job_relevant?"job-relevant":""}}"
    data-cat="${{a.category}}" data-company="${{a.company||""}}"
    data-topics="${{a.topics.join(",")}}"
    data-priority="${{a.priority_source}}"
    data-text="${{(a.title+" "+a.summary+" "+a.source).toLowerCase()}}">
    <div class="cat-bar ${{a.category}}"></div>
    <div class="card-meta">${{companyBadge}}<span class="source-badge">${{a.source}}</span><span class="pub-time">${{a.published}}</span></div>
    <div class="card-title"><a href="${{a.url}}" target="_blank">${{a.title}}</a></div>
    ${{summary}}${{topics}}
  </div>`;
}}

document.getElementById("news-grid").innerHTML =
  ARTICLES.map(renderArticle).join("") +
  `<div class="empty" id="news-empty"><div class="icon">🔍</div><div style="margin-top:10px">該当する記事が見つかりません</div></div>`;

document.getElementById("news-filters").addEventListener("click", e => {{
  const btn = e.target.closest("button");
  if (!btn) return;
  if (btn.dataset.cat !== undefined) {{
    activeCat = btn.dataset.cat;
    document.querySelectorAll("[data-cat]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    if (activeCat !== "target_company") {{ activeCompany = null; document.querySelectorAll("[data-company]").forEach(b=>b.classList.remove("active")); }}
  }} else if (btn.dataset.company) {{
    activeCompany = activeCompany === btn.dataset.company ? null : btn.dataset.company;
    document.querySelectorAll("[data-company]").forEach(b=>b.classList.remove("active"));
    if (activeCompany) {{ btn.classList.add("active"); activeCat="target_company"; document.querySelectorAll("[data-cat]").forEach(b=>b.classList.remove("active")); document.querySelector("[data-cat='target_company']").classList.add("active"); }}
  }} else if (btn.dataset.topic) {{
    const t = btn.dataset.topic;
    activeTopics.has(t) ? (activeTopics.delete(t), btn.classList.remove("active")) : (activeTopics.add(t), btn.classList.add("active"));
  }}
  applyNewsFilter();
}});

function applyNewsFilter() {{
  let visible = 0;
  document.querySelectorAll("#news-grid .card").forEach(card => {{
    const ok = (activeCat==="all"
        ||(activeCat==="job"&&card.classList.contains("job-relevant"))
        ||(activeCat==="priority"&&card.dataset.priority==="true")
        ||card.dataset.cat===activeCat)
      && (!activeCompany||card.dataset.company===activeCompany)
      && (activeTopics.size===0||[...activeTopics].every(t=>card.dataset.topics.split(",").includes(t)))
      && (!searchQuery||card.dataset.text.includes(searchQuery));
    card.style.display = ok ? "" : "none";
    if(ok) visible++;
  }});
  document.getElementById("news-empty").style.display = visible===0 ? "flex" : "none";
}}

// ══════════════ JOBS LOGIC ══════════════
let activeJCompany = "all", activeDept = "all", activeRemote = false, activeJapan = false;

// Stats
const jCounts = {{}};
JOBS.forEach(j => jCounts[j.company] = (jCounts[j.company]||0)+1);
let statsHtml = `<div class="stat-card"><div class="num">${{JOBS.length}}</div><div class="label">総求人数</div></div>`;
["OpenAI","Anthropic","Google DeepMind"].forEach(c => {{
  const col = CO_COLORS[c]||"#6366f1";
  statsHtml += `<div class="stat-card" style="border-color:${{col}}"><div class="num" style="color:${{col}}">${{jCounts[c]||0}}</div><div class="label">${{c}}</div></div>`;
}});
statsHtml += `<div class="stat-card" style="border-color:#94a3b8"><div class="num" style="color:#94a3b8">🔗</div><div class="label"><a href="{GOOGLE_CAREERS_URL}" target="_blank" style="color:#94a3b8">Google Careers →</a></div></div>`;
document.getElementById("job-stats").innerHTML = statsHtml;

function renderJob(j) {{
  const co    = CO_COLORS[j.company] || "#6366f1";
  const coCls = j.company.replace(/\\s+/g,"-");
  const remote = j.is_remote ? `<span class="remote-badge">🏠 Remote</span>` : "";
  const desc   = j.description ? `<div class="job-desc">${{j.description}}</div>` : "";
  const isJapan = /japan|tokyo|日本|東京/i.test(j.location);
  return `<div class="job-card"
    data-jcompany="${{j.company}}" data-dept="${{j.department}}"
    data-remote="${{j.is_remote}}" data-japan="${{isJapan}}"
    data-text="${{(j.title+" "+j.department+" "+j.location+" "+j.description).toLowerCase()}}">
    <div class="job-company-bar" style="background:${{co}}"></div>
    <div class="job-meta">
      <span class="job-company-badge ${{coCls}}" style="background:${{co}}">${{j.company}}</span>
      ${{j.department ? `<span class="job-dept">${{j.department}}</span>` : ""}}
      <span class="job-date">${{j.posted}}</span>
    </div>
    <div class="job-title"><a href="${{j.url}}" target="_blank">${{j.title}}</a></div>
    <div class="job-location">📍 ${{j.location||"—"}} ${{remote}}</div>
    ${{desc}}
    <a class="apply-btn" href="${{j.url}}" target="_blank">応募ページを開く →</a>
  </div>`;
}}

const googleCard = `<div class="google-link-card">
  <div class="google-logo">🔍</div>
  <div style="font-size:15px;font-weight:700">Google / Google Brain</div>
  <p>Google本体の求人はAPIが非公開のため、<br>公式サイトで直接検索してください。</p>
  <a class="google-link-btn" href="{GOOGLE_CAREERS_URL}" target="_blank">Google Careers で探す →</a>
</div>`;

const jobsGrid = document.getElementById("jobs-grid");
jobsGrid.innerHTML = JOBS.map(renderJob).join("") + googleCard +
  `<div class="empty" id="jobs-empty"><div class="icon">🔍</div><div style="margin-top:10px">該当する求人が見つかりません</div></div>`;

document.getElementById("job-filters").addEventListener("click", e => {{
  const btn = e.target.closest("button");
  if (!btn) return;
  if (btn.dataset.jcompany !== undefined) {{
    activeJCompany = btn.dataset.jcompany;
    activeDept = "all";
    document.querySelectorAll("[data-jcompany]").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active");
    // show/hide dept groups
    document.querySelectorAll(".dept-group").forEach(g => {{
      g.style.display = (activeJCompany!=="all" && g.dataset.deptCompany===activeJCompany) ? "flex" : "none";
    }});
    document.querySelectorAll(".dept-btn,.dept-all-btn").forEach(b=>b.classList.remove("active"));
    document.querySelectorAll(".dept-all-btn").forEach(b=>b.classList.add("active"));
  }} else if (btn.dataset.dept !== undefined) {{
    activeDept = btn.dataset.dept;
    document.querySelectorAll(".dept-btn,.dept-all-btn").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active");
  }} else if (btn.dataset.jlocation !== undefined) {{
    activeJapan = !activeJapan;
    btn.classList.toggle("active", activeJapan);
  }} else if (btn.dataset.remote !== undefined) {{
    activeRemote = !activeRemote;
    btn.classList.toggle("active", activeRemote);
  }}
  applyJobFilter();
}});

function applyJobFilter() {{
  let visible = 0;
  document.querySelectorAll("#jobs-grid .job-card").forEach(card => {{
    const ok = (activeJCompany==="all" || card.dataset.jcompany===activeJCompany)
      && (activeDept==="all" || card.dataset.dept===activeDept)
      && (!activeJapan  || card.dataset.japan==="true")
      && (!activeRemote || card.dataset.remote==="true")
      && (!searchQuery  || card.dataset.text.includes(searchQuery));
    card.style.display = ok?"":"none";
    if(ok) visible++;
  }});
  document.getElementById("jobs-empty").style.display = visible===0 ? "flex" : "none";
}}

function applyFilters() {{
  if (currentTab==="news") applyNewsFilter();
  else if (currentTab==="jobs") applyJobFilter();
  else applyProfileSearch();
}}

// ══════════════ PROFILE LOGIC ══════════════
const PROFILES        = {profiles_json};
const ANALYSIS        = {company_analysis_js};
const AMAZON_COMP     = {amazon_comp_js};
const SALARY_JP       = {salary_jp_js};
const AMAZON_COMP_JP  = {amazon_comp_jp_js};
const JAPAN_BENCHMARK = {japan_benchmark_js};
const PROFILE_COMPANIES = Object.keys(PROFILES);
let activeProfile = PROFILE_COMPANIES[0] || "";
let profileSearch = "";

// Build nav buttons
const profileNav = document.getElementById("profile-nav");
PROFILE_COMPANIES.forEach((co, i) => {{
  const p = PROFILES[co];
  const btn = document.createElement("button");
  btn.className = "profile-nav-btn" + (i===0?" active":"");
  btn.dataset.co = co;
  btn.style.borderColor = p.color;
  if (i===0) btn.style.background = p.color;
  btn.textContent = co + " (" + p.sales_count + " Sales)";
  btn.addEventListener("click", () => {{
    activeProfile = co;
    document.querySelectorAll(".profile-nav-btn").forEach(b => {{
      b.classList.remove("active");
      b.style.background = "";
    }});
    btn.classList.add("active");
    btn.style.background = p.color;
    document.querySelectorAll(".profile-panel").forEach(el => el.classList.remove("active"));
    document.getElementById("panel-" + co.replace(/\s+/g,"-")).classList.add("active");
    profileSearch = searchQuery;
    applyProfileSearch();
  }});
  profileNav.appendChild(btn);
}});

// Build panels
const panelsContainer = document.getElementById("profile-panels");

function stars(n) {{
  return "★".repeat(n) + "☆".repeat(5-n);
}}

function buildProfilePanel(co) {{
  const p = PROFILES[co];
  const coId = co.replace(/\s+/g,"-");
  const remoteRatio = p.sales_count > 0 ? Math.round(p.remote_count/p.sales_count*100) : 0;
  const maxDept = Math.max(...Object.values(p.dept_breakdown), 1);

  // Department bars
  let deptHtml = "";
  for (const [dept, cnt] of Object.entries(p.dept_breakdown)) {{
    const pct = Math.round(cnt/maxDept*100);
    deptHtml += `<div class="dept-bar-row">
      <div class="dept-bar-label"><span>${{dept}}</span><span>${{cnt}}件</span></div>
      <div class="dept-bar-track"><div class="dept-bar-fill" style="width:${{pct}}%;background:${{p.color}}"></div></div>
    </div>`;
  }}

  // Match tips
  const matchTips = ["アカウント管理","ブランド戦略","マーケットプレイス","B2Bセールス","パートナー管理","デジタル広告"];
  const matchHtml = matchTips.map(t=>`<span class="match-tip">${{t}}</span>`).join("");

  // Sales job list
  let jobsHtml = `<div id="sjlist-${{coId}}">`;
  if (p.sales_jobs.length === 0) {{
    jobsHtml += `<div style="color:var(--muted);font-size:13px;padding:20px 0;text-align:center">Sales系求人は現在見つかりませんでした</div>`;
  }} else {{
    p.sales_jobs.forEach(j => {{
      const matchBadge  = j.is_match  ? `<span class="sj-match-badge">✨ あなたにマッチ</span>` : "";
      const japanBadge  = j.is_japan  ? `<span class="sj-match-badge" style="background:#1e3a5f;color:#93c5fd;border-color:#3b82f6">🇯🇵 東京・日本</span>` : "";
      const remoteBadge = j.is_remote ? `<span class="remote-badge">🏠 Remote</span>` : "";
      jobsHtml += `<div class="sales-job-item ${{j.is_match?"is-match":""}}" data-text="${{(j.title+" "+j.department+" "+j.location).toLowerCase()}}">
        <div class="sj-title-row">
          ${{japanBadge}}${{matchBadge}}
          <div class="sj-title"><a href="${{j.url}}" target="_blank">${{j.title}}</a></div>
        </div>
        <div class="sj-meta">
          ${{j.department ? `<span class="sj-dept">${{j.department}}</span>` : ""}}
          <span class="sj-loc">📍 ${{j.location||"—"}}</span>
          ${{remoteBadge}}
          <span class="sj-date">${{j.posted}}</span>
        </div>
      </div>`;
    }});
  }}
  jobsHtml += `</div>`;

  // News
  let newsHtml = "";
  if (p.news.length === 0) {{
    newsHtml = `<div style="color:var(--muted);font-size:12px">直近のニュースはありません</div>`;
  }} else {{
    p.news.forEach(n => {{
      const tags = n.topics.map(t => `<span class="news-item-tag ${{n.job_relevant?"job":""}}">${{t}}</span>`).join("");
      newsHtml += `<div class="news-item">
        <a href="${{n.url}}" target="_blank">${{n.title}}</a>
        <div class="news-item-meta"><span class="news-item-time">${{n.published}}</span>${{tags}}</div>
      </div>`;
    }});
  }}

  // Salary section
  const sal = p.salary || {{}};
  let salaryHtml = "";
  if (sal.roles && sal.roles.length) {{
    const qa = sal.quota_attainment;
    const qaCls = qa >= 75 ? "good" : qa >= 50 ? "warn" : "bad";
    const qaLabel = qa != null ? `クォータ達成率: ${{qa}}%` : "達成率: データなし";
    const adviceWarn = sal.entry_advice && sal.entry_advice.includes("⚠️");
    const ROLE_DESCRIPTIONS = {{
      "AE":                     "担当顧客に直接販売する営業",
      "Account Executive":      "担当顧客に直接販売する営業",
      "Enterprise AE":          "大企業向け担当営業",
      "Enterprise Account Executive": "大企業向け担当営業",
      "AE (Google Cloud)":      "Google Cloud担当営業",
      "CSM":                    "契約後の顧客支援・継続率向上",
      "Customer Success Manager":"契約後の顧客支援・継続率向上",
      "CSM (Google Cloud)":     "Google Cloud顧客の定着支援",
      "BDR / SDR":              "新規リード開拓・アポ取りが主業務",
      "Strategic Account Manager":"大口顧客の関係構築・拡大",
      "Sales Engineer":         "技術的な提案支援・デモ担当",
      "Account Executive (US)": "米国の担当顧客向け営業",
    }};
    const rolesHtml = sal.roles.map(r => {{
      const oteStr = r.ote_low != null
        ? `${{r.ote_high != null && r.ote_high !== r.ote_low ? "$" + r.ote_low + "K〜$" + r.ote_high + "K" : "$" + r.ote_low + "K"}}`
        : "データなし";
      const baseStr = r.base_low != null
        ? `Base: $${{r.base_low}}K${{r.base_high && r.base_high !== r.base_low ? "〜$" + r.base_high + "K" : ""}}`
        : "Base: データなし";
      const desc = ROLE_DESCRIPTIONS[r.role] || "";
      return `<div class="salary-role-card">
        <div class="role-name">${{r.role}}${{desc ? `<span style="display:block;font-size:10px;color:var(--muted);font-weight:400;margin-top:2px">${{desc}}</span>` : ""}}</div>
        <div class="ote-val">${{oteStr}} <span style="font-size:11px;font-weight:400;color:var(--muted)">OTE</span></div>
        <div class="base-val">${{baseStr}}</div>
        ${{r.note ? `<div class="role-note">${{r.note}}</div>` : ""}}
      </div>`;
    }}).join("");
    const amazBase = AMAZON_COMP.base_low != null
      ? `${{AMAZON_COMP.base_low}}K〜$${{AMAZON_COMP.base_high}}K` : "—";
    // Japan salary panel
    const jpSal = SALARY_JP[co] || {{}};
    const hasOffice = jpSal.has_office;
    const hiringStatus = jpSal.hiring_status || "none";
    const statusLabel = hiringStatus === "actively_hiring" ? "🔥 積極採用中" : hiringStatus === "active" ? "✅ 採用あり" : "❌ 日本採用なし";
    const statusCls   = hiringStatus === "actively_hiring" ? "hiring" : hiringStatus === "active" ? "active" : "none";
    const jpAdviceWarn = (jpSal.entry_advice||"").startsWith("現時点");
    let jpRolesHtml = "";
    if (jpSal.roles && jpSal.roles.length) {{
      jpRolesHtml = `<div class="salary-roles">` + jpSal.roles.map(r => {{
        const oteStr = r.ote_low != null ? `¥${{r.ote_low}}万〜¥${{r.ote_high}}万` : "データなし";
        return `<div class="salary-role-card">
          <div class="role-name">${{r.role}}</div>
          <div class="ote-val" style="font-size:17px">${{oteStr}} <span style="font-size:11px;font-weight:400;color:var(--muted)">OTE</span></div>
          ${{r.note ? `<div class="role-note">${{r.note}}</div>` : ""}}
        </div>`;
      }}).join("") + `</div>`;
    }} else {{
      jpRolesHtml = `<div style="color:var(--muted);font-size:12px;padding:12px 0">日本向け求人データなし</div>`;
    }}
    const benchmarkRows = JAPAN_BENCHMARK.map(b =>
      `<tr><td style="color:var(--muted)">${{b.company}}</td><td style="font-weight:600">${{b.role}}</td><td style="color:#fbbf24">¥${{b.ote_low}}万〜¥${{b.ote_high}}万</td><td style="color:var(--muted)">${{b.note}}</td></tr>`
    ).join("");
    const jpPanel = `
      <div class="jp-office-status">
        <span class="jp-status-badge ${{statusCls}}">${{statusLabel}}</span>
        <span style="font-size:11px;color:var(--muted)">${{jpSal.office_note||""}}</span>
      </div>
      ${{jpSal.entry_advice ? `<div class="advice-box ${{jpAdviceWarn?"warn":""}}">${{jpSal.entry_advice}}</div>` : ""}}
      ${{jpRolesHtml}}
      <div class="amazon-compare" style="margin-top:10px">現職 Amazon Brand Specialist (3年目): <span>¥${{AMAZON_COMP_JP.low}}万〜¥${{AMAZON_COMP_JP.high}}万</span> — ${{AMAZON_COMP_JP.note}}</div>
      <details style="margin-top:12px">
        <summary style="font-size:11px;color:var(--muted);cursor:pointer">📊 外資IT日本Sales年収ベンチマーク（参考）</summary>
        <table class="benchmark-table" style="margin-top:8px">
          <thead><tr><th>企業</th><th>職種</th><th>OTE（万円）</th><th>備考</th></tr></thead>
          <tbody>${{benchmarkRows}}</tbody>
        </table>
      </details>
      ${{jpSal.openwork_url ? `<div style="margin-top:8px"><a class="salary-link" href="${{jpSal.openwork_url}}" target="_blank">📊 OpenWork（口コミ）</a></div>` : ""}}
    `;

    salaryHtml = `<div class="salary-section">
      <h3>💰 年収データ</h3>
      <div class="salary-tab-row" id="saltabs-${{coId}}">
        <button class="salary-tab active" data-stab="us" data-co="${{coId}}">🇺🇸 アメリカ採用（USD）</button>
        <button class="salary-tab" data-stab="jp" data-co="${{coId}}">🇯🇵 日本採用（JPY）</button>
      </div>
      <div class="salary-panel active" id="sal-us-${{coId}}">
        <div class="us-disclaimer">⚠️ <strong>アメリカ本社採用・USD建ての年収です。</strong> 日本採用は🇯🇵タブを参照。データ出所: RepVue / Glassdoor 2025-2026。</div>
        <div class="salary-meta">
          ${{qa != null ? `<span class="quota-badge ${{qaCls}}">${{qaLabel}}</span>` : ""}}
          ${{sal.avg_quota_m ? `<span style="font-size:11px;color:var(--muted)">年間クォータ: ~$$${{sal.avg_quota_m}}M</span>` : ""}}
          <div class="salary-links">
            ${{sal.repvue_url ? `<a class="salary-link" href="${{sal.repvue_url}}" target="_blank">📊 RepVue</a>` : ""}}
            ${{sal.glassdoor_url ? `<a class="salary-link" href="${{sal.glassdoor_url}}" target="_blank">🏢 Glassdoor</a>` : ""}}
          </div>
        </div>
        ${{sal.entry_advice ? `<div class="advice-box ${{adviceWarn?"warn":""}}">🇺🇸 ${{sal.entry_advice}}</div>` : ""}}
        <div class="salary-roles">${{rolesHtml}}</div>
        <div class="amazon-compare">現職 Amazon Brand Specialist (3年目) 米国参考: <span>$${{amazBase}}</span> — ${{AMAZON_COMP.note}}</div>
      </div>
      <div class="salary-panel" id="sal-jp-${{coId}}">${{jpPanel}}</div>
    </div>`;
  }}

  // 企業分析（3C/SWOT/4P）セクション
  const an = ANALYSIS[co] || {{}};
  let analysisHtml = "";
  if (an.c3) {{
    const tabId = `an-${{coId}}`;

    // 3C（タブ切り替え）
    const c3Sections = [
      ["company",    "🏢 Company（自社）",   an.c3.company||[]],
      ["customer",   "👥 Customer（顧客）",  an.c3.customer||[]],
      ["competitor", "⚔️ Competitor（競合）", an.c3.competitor||[]],
    ];
    const c3TabButtons = c3Sections.map(([key, label], i) =>
      `<button class="c3-tab${{i===0?" active":""}}" data-c3tab="${{key}}" data-c3co="${{coId}}">${{label}}</button>`
    ).join("");
    const c3Panels = c3Sections.map(([key, , pts], i) =>
      `<div class="c3-panel${{i===0?" active":""}}" id="c3-${{key}}-${{coId}}">
        <div class="c3-card"><ul>${{pts.map(p=>`<li>${{p}}</li>`).join("")}}</ul></div>
      </div>`
    ).join("");
    const c3Html = `<div class="c3-tab-row" id="c3tabs-${{coId}}">${{c3TabButtons}}</div>${{c3Panels}}`;

    // SWOT
    const sw = an.swot || {{}};
    const swotHtml = `<div class="swot-grid">` + [
      ["s","💪 Strengths（強み）", sw.strengths||[]],
      ["w","⚠️ Weaknesses（弱み）", sw.weaknesses||[]],
      ["o","🚀 Opportunities（機会）", sw.opportunities||[]],
      ["t","🔥 Threats（脅威）", sw.threats||[]],
    ].map(([cls,title,pts]) => `<div class="swot-card ${{cls}}">
      <h4>${{title}}</h4>
      <ul>${{pts.map(p=>`<li>${{p}}</li>`).join("")}}</ul>
    </div>`).join("") + `</div>`;

    // 4P
    const pp = an.p4 || {{}};
    const p4Html = `<div class="p4-grid">` + [
      ["📦 Product（製品）", pp.product||""],
      ["💴 Price（価格）",   pp.price||""],
      ["🏪 Place（販路）",   pp.place||""],
      ["📣 Promotion（プロモーション）", pp.promotion||""],
    ].map(([title,text]) => `<div class="p4-card"><h4>${{title}}</h4><p>${{text}}</p></div>`).join("") + `</div>`;

    // 面接Tips
    const tipsHtml = `<div class="tips-list">` +
      (an.interview_tips||[]).map((t,i)=>`<div class="tip-item"><span class="tip-num">Q${{i+1}}.</span>${{t}}</div>`).join("") +
      `</div>`;

    analysisHtml = `<div class="analysis-section">
      <h3>📊 企業分析</h3>
      ${{an.tagline ? `<div class="snapshot-bar">💡 ${{an.tagline}} ／ ${{an.snapshot||""}}</div>` : ""}}
      <div class="analysis-tab-row" id="antabs-${{coId}}">
        <button class="analysis-tab active" data-atab="c3" data-aco="${{coId}}">3C分析</button>
        <button class="analysis-tab" data-atab="swot" data-aco="${{coId}}">SWOT分析</button>
        <button class="analysis-tab" data-atab="p4" data-aco="${{coId}}">4P分析</button>
        <button class="analysis-tab" data-atab="tips" data-aco="${{coId}}">💬 面接対策</button>
      </div>
      <div class="analysis-panel active" id="an-c3-${{coId}}">${{c3Html}}</div>
      <div class="analysis-panel" id="an-swot-${{coId}}">${{swotHtml}}</div>
      <div class="analysis-panel" id="an-p4-${{coId}}">${{p4Html}}</div>
      <div class="analysis-panel" id="an-tips-${{coId}}">${{tipsHtml}}</div>
    </div>`;
  }}

  const panel = document.createElement("div");
  panel.className = "profile-panel" + (co===PROFILE_COMPANIES[0]?" active":"");
  panel.id = "panel-" + coId;
  panel.innerHTML = `
    <div class="profile-header">
      <div class="co-dot" style="background:${{p.color}}"></div>
      <h2>${{co}}</h2>
      <div class="score" title="Sales採用おすすめ度">${{stars(p.score)}}</div>
    </div>
    <div class="profile-stats-row">
      <div class="ps-card"><div class="num" style="color:${{p.color}}">${{p.total_jobs}}</div><div class="lbl">総求人数</div></div>
      <div class="ps-card"><div class="num" style="color:#fbbf24">${{p.sales_count}}</div><div class="lbl">💼 Sales系求人</div></div>
      <div class="ps-card"><div class="num" style="color:var(--emerald)">${{p.remote_count}}</div><div class="lbl">🏠 リモート可</div></div>
      <div class="ps-card"><div class="num" style="color:var(--sky)">${{remoteRatio}}%</div><div class="lbl">リモート率</div></div>
    </div>
    <div class="profile-body">
      <div>
        <div class="dept-chart-box">
          <h3>📊 Sales部門内訳</h3>
          ${{deptHtml || '<div style="color:var(--muted);font-size:12px">データなし</div>'}}
          <div class="remote-stat">
            <div class="label">🏠 リモート率 (${{remoteRatio}}%)</div>
            <div class="remote-bar"><div class="remote-bar-fill" style="width:${{remoteRatio}}%"></div></div>
          </div>
          <div class="match-box">
            <h4>✨ あなたの強みが活きるキーワード</h4>
            ${{matchHtml}}
          </div>
        </div>
        <div class="profile-news-box">
          <h3>📰 最新ニュース</h3>
          ${{newsHtml}}
        </div>
        ${{salaryHtml}}
        ${{analysisHtml}}
      </div>
      <div>
        <div class="sales-list-box">
          <h3>💼 Sales求人一覧 <span style="font-weight:400;color:var(--muted)">（${{p.sales_jobs.length}}件 / ✨マッチ優先）</span></h3>
          ${{jobsHtml}}
        </div>
      </div>
    </div>`;
  panelsContainer.appendChild(panel);
}}

PROFILE_COMPANIES.forEach(buildProfilePanel);

function applyProfileSearch() {{
  const q = searchQuery.trim().toLowerCase();
  document.querySelectorAll(".sales-job-item").forEach(el => {{
    el.style.display = (!q || el.dataset.text.includes(q)) ? "" : "none";
  }});
}}

// Salary US/JP tab switching
document.addEventListener("click", e => {{
  const btn = e.target.closest(".salary-tab");
  if (!btn) return;
  const coId = btn.dataset.co;
  const stab = btn.dataset.stab;
  document.querySelectorAll(`[data-co="${{coId}}"].salary-tab`).forEach(b => b.classList.toggle("active", b===btn));
  document.getElementById(`sal-us-${{coId}}`).classList.toggle("active", stab==="us");
  document.getElementById(`sal-jp-${{coId}}`).classList.toggle("active", stab==="jp");
}});

// 3C inner tab switching
document.addEventListener("click", e => {{
  const btn = e.target.closest(".c3-tab");
  if (!btn) return;
  const coId = btn.dataset.c3co;
  const key  = btn.dataset.c3tab;
  document.querySelectorAll(`[data-c3co="${{coId}}"].c3-tab`).forEach(b => b.classList.toggle("active", b===btn));
  ["company","customer","competitor"].forEach(k => {{
    const el = document.getElementById(`c3-${{k}}-${{coId}}`);
    if (el) el.classList.toggle("active", k===key);
  }});
}});

// Analysis tab switching (3C/SWOT/4P/Tips)
document.addEventListener("click", e => {{
  const btn = e.target.closest(".analysis-tab");
  if (!btn) return;
  const coId = btn.dataset.aco;
  const atab = btn.dataset.atab;
  document.querySelectorAll(`[data-aco="${{coId}}"].analysis-tab`).forEach(b => b.classList.toggle("active", b===btn));
  ["c3","swot","p4","tips"].forEach(t => {{
    const el = document.getElementById(`an-${{t}}-${{coId}}`);
    if (el) el.classList.toggle("active", t===atab);
  }});
}});
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    logger.info("Dashboard saved: %s", output_path)
    return output_path
