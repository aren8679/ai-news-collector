"""
RSS feed collector.
Fetches articles published within the configured time window.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

from config import FeedSource, FETCH_HOURS, MAX_ARTICLES_PER_FEED, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    url: str
    published: datetime
    summary: str            # raw excerpt from the feed
    source_name: str
    category: str
    company: str = ""
    ai_summary: str = ""    # filled in by summarizer.py
    topics: list[str] = field(default_factory=list)
    priority_source: bool = False  # True = 注目ソース


def _clean_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    return " ".join(text.split())


def _parse_published(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """Return a timezone-aware datetime for the entry's publish time."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                import calendar
                ts = calendar.timegm(t)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                continue
    return None


def _fetch_feed(source: FeedSource, cutoff: datetime, headers: dict) -> list[Article]:
    """Download and parse a single RSS/Atom feed."""
    articles: list[Article] = []

    try:
        response = httpx.get(
            source.url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch %s (%s): %s", source.name, source.url, exc)
        return articles

    feed = feedparser.parse(response.text)

    if feed.bozo and not feed.entries:
        logger.warning("Feed parse error for %s: %s", source.name, feed.bozo_exception)
        return articles

    limit = source.max_articles if source.max_articles > 0 else MAX_ARTICLES_PER_FEED
    count = 0
    for entry in feed.entries:
        if count >= limit:
            break

        published = _parse_published(entry)
        if published is None:
            # No date info — include it but mark as unknown
            published = datetime.now(tz=timezone.utc)
        elif published < cutoff:
            continue

        title = _clean_html(getattr(entry, "title", "(no title)"))
        url = getattr(entry, "link", "")

        # Best-effort summary: prefer summary over content
        raw_summary = (
            getattr(entry, "summary", "")
            or (entry.content[0].value if getattr(entry, "content", None) else "")
        )
        summary = _clean_html(raw_summary)[:600]  # trim to reasonable length

        articles.append(
            Article(
                title=title,
                url=url,
                published=published,
                summary=summary,
                source_name=source.name,
                category=source.category,
                company=source.company,
                priority_source=source.priority,
            )
        )
        count += 1

    logger.info("  [%s] %d article(s) collected", source.name, len(articles))
    return articles


def collect_articles(feeds: list[FeedSource]) -> list[Article]:
    """Collect articles from all configured feeds published within FETCH_HOURS."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=FETCH_HOURS)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AINewsCollector/1.0; "
            "+https://github.com/your-handle/ai-news-collector)"
        )
    }

    all_articles: list[Article] = []
    for source in feeds:
        logger.info("Fetching: %s", source.name)
        articles = _fetch_feed(source, cutoff, headers)
        all_articles.extend(articles)

    # Sort newest first
    all_articles.sort(key=lambda a: a.published, reverse=True)
    logger.info("Total articles collected: %d", len(all_articles))
    return all_articles
