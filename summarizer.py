"""
Article processor — no external API required.

For each article:
  - ai_summary: RSS description をそのまま整形して使用（英語はそのまま）
  - topics: タイトル＋descriptionのキーワードマッチで自動付与
"""

from __future__ import annotations

import logging
import re
import textwrap

from collector import Article

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Topic keyword rules: (tag, [keywords to match against title+description])
# キーワードは小文字で記述。タイトル/descriptionも小文字化して照合する。
# ---------------------------------------------------------------------------
TOPIC_RULES: list[tuple[str, list[str]]] = [
    # --- 転職活動に直結するトピック（reporter.pyでハイライト表示） ---
    ("採用・人事",     ["hiring", "recruit", "job", "career", "headcount", "layoff", "laid off",
                        "fired", "workforce", "employees", "staff", "talent", "cto", "ceo", "vp of",
                        "chief", "appoint", "join", "採用", "転職", "求人", "退職", "解雇", "人事"]),
    ("新プロダクト",   ["launch", "announce", "release", "introduces", "unveil", "debut",
                        "now available", "shipping", "rolls out", "発表", "リリース", "ローンチ", "公開"]),
    ("資金調達",       ["funding", "raises", "raised", "investment", "series a", "series b",
                        "series c", "valuation", "ipo", "billion", "venture", "資金調達", "投資", "億円"]),
    ("組織変更",       ["restructur", "reorg", "reorganiz", "spin", "acqui", "merger", "acquires",
                        "bought", "partnership", "joint venture", "組織", "買収", "合併", "提携"]),
    # --- 技術トピック ---
    ("LLM",           ["llm", "large language model", "gpt", "claude", "gemini", "llama",
                        "mistral", "language model", "foundation model", "chatgpt"]),
    ("画像生成",       ["image generation", "text-to-image", "diffusion", "dall-e", "midjourney",
                        "stable diffusion", "imagen", "sora", "video generation", "画像生成"]),
    ("音声AI",         ["speech", "voice", "audio", "tts", "text-to-speech", "whisper",
                        "音声", "speech recognition"]),
    ("エージェント",   ["agent", "agentic", "autonomous", "multi-agent", "computer use",
                        "tool use", "エージェント"]),
    ("コーディングAI", ["code", "coding", "copilot", "devin", "cursor", "github copilot",
                        "programming", "developer", "software engineer"]),
    ("マルチモーダル", ["multimodal", "multi-modal", "vision", "image understanding",
                        "video understanding", "マルチモーダル"]),
    ("規制・政策",     ["regulation", "policy", "law", "legislation", "government", "congress",
                        "senate", "eu ai act", "executive order", "ban", "規制", "政策"]),
    ("研究・論文",     ["research", "paper", "arxiv", "benchmark", "study", "findings",
                        "experiment", "dataset", "researchers", "論文", "研究"]),
    ("安全性・倫理",   ["safety", "alignment", "bias", "harmful", "ethics", "risk",
                        "responsible", "jailbreak", "hallucination", "安全", "倫理"]),
    ("オープンソース", ["open source", "open-source", "open weight", "hugging face",
                        "github", "apache", "mit license", "オープンソース"]),
    ("ハードウェア",   ["chip", "gpu", "tpu", "npu", "nvidia", "amd", "intel", "hardware",
                        "semiconductor", "h100", "b200", "ハードウェア"]),
    ("ロボット",       ["robot", "robotics", "humanoid", "boston dynamics", "figure",
                        "physical ai", "ロボット"]),
    ("医療AI",         ["medical", "health", "clinical", "drug", "diagnosis", "patient",
                        "hospital", "cancer", "医療", "ヘルスケア"]),
    ("教育AI",         ["education", "learning", "student", "teacher", "school", "tutor",
                        "教育", "学習"]),
    ("自動運転",       ["autonomous vehicle", "self-driving", "waymo", "tesla autopilot",
                        "autonomous driving", "自動運転"]),
]

# 転職活動に直結するトピックタグ（reporter.pyがハイライト判定に使用）
JOB_RELEVANT_TOPICS: set[str] = {"採用・人事", "新プロダクト", "資金調達", "組織変更"}


def _detect_topics(text: str, max_topics: int = 4) -> list[str]:
    """Return matching topic tags based on keyword presence in text."""
    lower = text.lower()
    matched = [tag for tag, keywords in TOPIC_RULES if any(kw in lower for kw in keywords)]
    return matched[:max_topics]


def _format_summary(raw: str) -> str:
    """
    Trim and lightly format the RSS description for display.
    - Collapse whitespace
    - Wrap long text to ~120 chars per line
    - Cap at 3 lines
    """
    if not raw:
        return ""
    # Collapse whitespace
    text = " ".join(raw.split())
    # Wrap into lines of ~120 chars
    lines = textwrap.wrap(text, width=120)
    # Cap at 3 lines
    return "\n".join(lines[:3])


def summarize_articles(articles: list[Article]) -> list[Article]:
    """
    Populate ai_summary and topics for each article using RSS data only.
    No external API calls are made.
    """
    for article in articles:
        # ai_summary: formatted RSS description (English articles kept as-is)
        article.ai_summary = _format_summary(article.summary)

        # topics: keyword match on title + description
        combined = f"{article.title} {article.summary}"
        article.topics = _detect_topics(combined)

    logger.info("Processed %d article(s) (RSS-based, no API)", len(articles))
    return articles
