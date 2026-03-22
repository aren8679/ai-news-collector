"""
Configuration management for AI News Collector.
Loads settings from environment variables and defines RSS feed sources.
"""

import os
from dataclasses import dataclass, field


@dataclass
class FeedSource:
    name: str
    url: str
    category: str           # "target_company", "overseas", "japan"
    company: str = ""       # e.g. "OpenAI" — for target company blogs
    max_articles: int = 0   # 0 = use global MAX_ARTICLES_PER_FEED
    priority: bool = False  # True = 注目ソース（別枠で目立つ表示）


RSS_FEEDS: list[FeedSource] = [
    # ================================================================
    # 【注目】プライオリティソース — 別枠で目立つ表示
    # ================================================================
    FeedSource(
        name="Bloomberg Technology",
        url="https://feeds.bloomberg.com/technology/news.rss",
        category="overseas",
        priority=True,
        max_articles=15,
    ),
    FeedSource(
        name="Financial Times Technology",
        url="https://www.ft.com/technology?format=rss",
        category="overseas",
        priority=True,
        max_articles=15,
    ),
    # ================================================================
    # 【最優先】転職ターゲット企業公式ブログ — 多めに収集
    # ================================================================
    FeedSource(
        name="OpenAI Blog",
        url="https://openai.com/news/rss.xml",
        category="target_company",
        company="OpenAI",
        max_articles=30,
    ),
    FeedSource(
        name="Anthropic Blog",
        url="https://www.anthropic.com/news/rss",
        category="target_company",
        company="Anthropic",
        max_articles=30,
    ),
    FeedSource(
        name="Google DeepMind Blog",
        url="https://deepmind.google/blog/rss.xml",
        category="target_company",
        company="Google DeepMind",
        max_articles=30,
    ),
    FeedSource(
        name="Google AI Blog",
        url="https://blog.google/technology/ai/rss/",
        category="target_company",
        company="Google",
        max_articles=30,
    ),
    FeedSource(
        name="Meta AI Blog",
        url="https://engineering.fb.com/category/ai-research/feed/",
        category="target_company",
        company="Meta AI",
        max_articles=20,
    ),
    FeedSource(
        name="Microsoft AI Blog",
        url="https://blogs.microsoft.com/ai/feed/",
        category="target_company",
        company="Microsoft",
        max_articles=20,
    ),
    FeedSource(
        name="Apple Machine Learning Research",
        url="https://machinelearning.apple.com/rss.xml",
        category="target_company",
        company="Apple",
        max_articles=20,
    ),
    FeedSource(
        name="Nvidia AI Blog",
        url="https://blogs.nvidia.com/feed/",
        category="target_company",
        company="Nvidia",
        max_articles=20,
    ),
    FeedSource(
        name="Hugging Face Blog",
        url="https://huggingface.co/blog/feed.xml",
        category="target_company",
        company="Hugging Face",
        max_articles=20,
    ),
    # ================================================================
    # 【優先】AI業界ニュース
    # ================================================================
    FeedSource(
        name="TechCrunch AI",
        url="https://techcrunch.com/category/artificial-intelligence/feed/",
        category="overseas",
        priority=True,
        max_articles=15,
    ),
    FeedSource(
        name="The Verge AI",
        url="https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        category="overseas",
    ),
    FeedSource(
        name="Ars Technica AI",
        url="https://feeds.arstechnica.com/arstechnica/technology-lab",
        category="overseas",
    ),
    FeedSource(
        name="VentureBeat AI",
        url="https://venturebeat.com/category/ai/feed/",
        category="overseas",
    ),
    # ================================================================
    # 日本語AIニュース
    # ================================================================
    FeedSource(
        name="Ledge.ai",
        url="https://ledge.ai/feed/",
        category="japan",
    ),
    FeedSource(
        name="AI-SCHOLAR",
        url="https://ai-scholar.tech/feed",
        category="japan",
    ),
    FeedSource(
        name="ITmedia AI+",
        url="https://rss.itmedia.co.jp/rss/2.0/aiplus.xml",
        category="japan",
    ),
]

# --- Collector settings ---
FETCH_HOURS: int = int(os.getenv("FETCH_HOURS", "24"))
MAX_ARTICLES_PER_FEED: int = int(os.getenv("MAX_ARTICLES_PER_FEED", "10"))
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))

# --- Output settings ---
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "reports")
