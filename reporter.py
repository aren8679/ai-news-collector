"""
Markdown report generator.
Takes a list of summarized Articles and produces a daily report file.

Section order:
  0. 🔥 注目ソース速報（priority feeds: Bloomberg / FT / TechCrunch）
  1. 💼 転職活動チェックポイント（job-relevant highlights across all categories）
  2. 🎯 転職ターゲット企業の最新動向（target_company）
  3. 🌐 AI業界ニュース（overseas）
  4. 🇯🇵 日本語AIニュース（japan）
  5. 📌 トピック別インデックス
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from collector import Article
from config import OUTPUT_DIR
from summarizer import JOB_RELEVANT_TOPICS

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

CATEGORY_LABELS: dict[str, str] = {
    "target_company": "🎯 転職ターゲット企業の最新動向",
    "overseas":       "🌐 AI業界ニュース",
    "japan":          "🇯🇵 日本語AIニュース",
}

CATEGORY_ORDER = ["target_company", "overseas", "japan"]

# 転職関連トピックに付けるバッジ
TOPIC_BADGES: dict[str, str] = {
    "採用・人事": "💼",
    "新プロダクト": "🚀",
    "資金調達": "💰",
    "組織変更": "🔄",
}


def _is_job_relevant(article: Article) -> bool:
    return bool(JOB_RELEVANT_TOPICS & set(article.topics))


def _format_topic_tags(topics: list[str]) -> str:
    parts = []
    for t in topics:
        badge = TOPIC_BADGES.get(t, "")
        parts.append(f"`{badge}{t}`" if badge else f"`{t}`")
    return " ".join(parts)


def _format_article(article: Article, index: int, *, show_job_flag: bool = True) -> str:
    job_relevant = show_job_flag and _is_job_relevant(article)
    heading_prefix = "⭐ " if job_relevant else ""

    lines = [
        f"### {index}. {heading_prefix}{article.title}",
        f"- **ソース**: {article.source_name}",
        f"- **公開日時**: {article.published.astimezone(JST).strftime('%Y-%m-%d %H:%M JST')}",
        f"- **URL**: {article.url}",
    ]

    if article.topics:
        lines.append(f"- **トピック**: {_format_topic_tags(article.topics)}")

    lines.append("")

    if article.ai_summary:
        for line in article.ai_summary.split("\n"):
            if line.strip():
                lines.append(f"> {line.strip()}")
    else:
        lines.append("> （概要なし）")

    lines.append("")
    return "\n".join(lines)


def _build_priority_section(articles: list[Article]) -> str:
    """🔥 注目ソース速報: Bloomberg / FT / TechCrunch など priority=True フィードの記事一覧。"""
    priority = [a for a in articles if a.priority_source]
    if not priority:
        return ""

    lines = ["## 🔥 注目ソース速報\n"]
    lines.append("> Bloomberg Technology・Financial Times・TechCrunch など主要メディアの最新記事です。\n")

    for article in priority:
        pub = article.published.astimezone(JST).strftime("%m/%d %H:%M")
        tags = _format_topic_tags(article.topics) if article.topics else ""
        job_mark = "⭐ " if _is_job_relevant(article) else ""
        lines.append(f"- {job_mark}[{article.title}]({article.url})  ")
        lines.append(f"  **{article.source_name}** ({pub} JST){(' — ' + tags) if tags else ''}")
        if article.ai_summary:
            first_line = article.ai_summary.split("\n")[0].strip()
            lines.append(f"  > {first_line}")
        lines.append("")

    return "\n".join(lines)


def _build_job_highlights(articles: list[Article]) -> str:
    """
    転職活動チェックポイント：全カテゴリから転職関連記事を抜き出して冒頭にまとめる。
    """
    relevant = [a for a in articles if _is_job_relevant(a)]
    if not relevant:
        return ""

    lines = ["## 💼 転職活動チェックポイント\n"]
    lines.append("> 採用・新プロダクト・資金調達・組織変更に関する記事をピックアップしました。\n")

    for article in relevant:
        pub = article.published.astimezone(JST).strftime("%m/%d %H:%M")
        tags = _format_topic_tags(article.topics)
        company_prefix = f"**[{article.company}]** " if article.company else ""
        lines.append(f"- {company_prefix}[{article.title}]({article.url})  ")
        lines.append(f"  {tags} — {article.source_name} ({pub} JST)")
        if article.ai_summary:
            first_line = article.ai_summary.split("\n")[0].strip()
            lines.append(f"  > {first_line}")
        lines.append("")

    return "\n".join(lines)


def _build_topic_index(articles: list[Article]) -> str:
    topic_map: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        for topic in article.topics:
            topic_map[topic].append(article)

    if not topic_map:
        return ""

    # Job-relevant topics first, then the rest alphabetically
    job_topics = sorted(t for t in topic_map if t in JOB_RELEVANT_TOPICS)
    other_topics = sorted(t for t in topic_map if t not in JOB_RELEVANT_TOPICS)

    lines = ["## 📌 トピック別インデックス\n"]
    for topic in job_topics + other_topics:
        arts = topic_map[topic]
        badge = TOPIC_BADGES.get(topic, "")
        lines.append(f"### {badge}{topic} ({len(arts)}件)\n")
        for art in arts:
            lines.append(f"- [{art.title}]({art.url})")
        lines.append("")

    return "\n".join(lines)


def generate_report(articles: list[Article], report_date: datetime | None = None) -> Path:
    """Generate a Markdown daily report and write it to OUTPUT_DIR."""
    if report_date is None:
        report_date = datetime.now(tz=JST)

    date_str = report_date.strftime("%Y-%m-%d")
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_str}_ai_news.md"

    by_category: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        by_category[article.category].append(article)

    total = len(articles)
    job_count = sum(1 for a in articles if _is_job_relevant(a))
    generated_at = datetime.now(tz=JST).strftime("%Y-%m-%d %H:%M JST")

    sections: list[str] = []

    # ---- Header ----
    sections.append(f"# AI ニュース デイリーレポート — {date_str}\n")
    sections.append(f"> 生成日時: {generated_at}  ")
    sections.append(f"> 収集記事数: **{total}件**（うち転職関連: **{job_count}件**）\n")
    sections.append("---\n")

    # ---- Table of contents ----
    priority_count = sum(1 for a in articles if a.priority_source)
    sections.append("## 目次\n")
    if priority_count:
        sections.append("- [🔥 注目ソース速報](#-注目ソース速報)")
    if job_count:
        sections.append("- [💼 転職活動チェックポイント](#-転職活動チェックポイント)")
    for cat_key in CATEGORY_ORDER:
        if cat_key in by_category:
            label = CATEGORY_LABELS[cat_key]
            count = len(by_category[cat_key])
            sections.append(f"- [{label} ({count}件)](#{_anchor(label)})")
    if any(a.topics for a in articles):
        sections.append("- [📌 トピック別インデックス](#-トピック別インデックス)")
    sections.append("")

    # ---- Priority sources ----
    priority_section = _build_priority_section(articles)
    if priority_section:
        sections.append(priority_section)
        sections.append("---\n")

    # ---- Job highlights ----
    job_highlights = _build_job_highlights(articles)
    if job_highlights:
        sections.append(job_highlights)
        sections.append("---\n")

    # ---- Articles by category ----
    for cat_key in CATEGORY_ORDER:
        cat_articles = by_category.get(cat_key, [])
        if not cat_articles:
            continue

        label = CATEGORY_LABELS[cat_key]
        sections.append(f"## {label}\n")

        # For target_company: group by company
        if cat_key == "target_company":
            company_groups: dict[str, list[Article]] = defaultdict(list)
            for a in cat_articles:
                company_groups[a.company or "その他"].append(a)

            global_idx = 1
            for company in ["OpenAI", "Anthropic", "Google DeepMind", "Google"]:
                arts = company_groups.get(company, [])
                if not arts:
                    continue
                sections.append(f"### {company}\n")
                for art in arts:
                    sections.append(_format_article(art, global_idx))
                    global_idx += 1
        else:
            for idx, article in enumerate(cat_articles, 1):
                sections.append(_format_article(article, idx))

        sections.append("---\n")

    # ---- Topic index ----
    topic_index = _build_topic_index(articles)
    if topic_index:
        sections.append(topic_index)

    # ---- Footer ----
    sections.append("\n---")
    sections.append(
        "*このレポートは [ai-news-collector](https://github.com/your-handle/ai-news-collector) "
        "により自動生成されました。*"
    )

    content = "\n".join(sections)
    output_path.write_text(content, encoding="utf-8")
    logger.info("Report saved: %s", output_path)
    return output_path


def _anchor(label: str) -> str:
    anchor = label.lower()
    anchor = re.sub(r"[^\w\s\u3000-\u9fff-]", "", anchor)
    anchor = re.sub(r"\s+", "-", anchor.strip())
    return anchor
