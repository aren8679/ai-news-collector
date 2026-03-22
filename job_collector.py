"""
Job listing collector for target companies.

Sources:
  - OpenAI        : Ashby ATS   public API  (645+ jobs)
  - Anthropic     : Greenhouse  public API  (437+ jobs)
  - Google DeepMind: Greenhouse public API  (100+ jobs)
  - Google        : careers.google.com search link (API非公開のためリンクのみ)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
REQUEST_TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AINewsCollector/1.0)"}

# Google公式求人検索ページURL（APIが非公開のためリンクのみ提供）
GOOGLE_CAREERS_URL = "https://www.google.com/about/careers/applications/jobs/results/?q=machine+learning+AI&location=&target_level=EARLY&target_level=MID"


@dataclass
class Job:
    title: str
    company: str
    location: str
    department: str
    url: str
    posted_date: Optional[datetime] = None
    is_remote: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# OpenAI — Ashby ATS public API
# ---------------------------------------------------------------------------
def fetch_openai_jobs() -> list[Job]:
    jobs: list[Job] = []
    try:
        r = httpx.get(
            "https://api.ashbyhq.com/posting-api/job-board/openai",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        for item in r.json().get("jobs", []):
            if not item.get("isListed", True):
                continue
            jobs.append(Job(
                title=item.get("title", ""),
                company="OpenAI",
                location=item.get("location", ""),
                department=item.get("department", item.get("team", "")),
                url=item.get("jobUrl", ""),
                posted_date=_iso(item.get("publishedAt")),
                is_remote=item.get("isRemote", False) or item.get("workplaceType") == "Remote",
                description=_strip(item.get("descriptionPlain", ""))[:200],
            ))
    except Exception as e:
        logger.warning("OpenAI jobs fetch failed: %s", e)
    logger.info("  [OpenAI] %d jobs", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Anthropic — Greenhouse public API
# ---------------------------------------------------------------------------
def fetch_anthropic_jobs() -> list[Job]:
    return _greenhouse_jobs("anthropic", "Anthropic")


# ---------------------------------------------------------------------------
# Google DeepMind — Greenhouse public API
# ---------------------------------------------------------------------------
def fetch_deepmind_jobs() -> list[Job]:
    return _greenhouse_jobs("deepmind", "Google DeepMind")


def _greenhouse_jobs(board: str, company: str) -> list[Job]:
    jobs: list[Job] = []
    try:
        r = httpx.get(
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        for item in r.json().get("jobs", []):
            depts = item.get("departments") or []
            dept  = depts[0]["name"] if depts else ""
            loc_data = item.get("location", {})
            loc  = loc_data.get("name", "") if isinstance(loc_data, dict) else str(loc_data)
            jobs.append(Job(
                title=item.get("title", ""),
                company=company,
                location=loc,
                department=dept,
                url=item.get("absolute_url", ""),
                posted_date=_iso(item.get("first_published") or item.get("updated_at")),
                is_remote="remote" in loc.lower(),
                description=_strip(item.get("content", ""))[:200],
            ))
    except Exception as e:
        logger.warning("%s jobs fetch failed: %s", company, e)
    logger.info("  [%s] %d jobs", company, len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Mistral AI — Lever public API (returns a bare list)
# ---------------------------------------------------------------------------
def fetch_mistral_jobs() -> list[Job]:
    jobs: list[Job] = []
    try:
        r = httpx.get(
            "https://api.lever.co/v0/postings/mistral?mode=json",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        for item in r.json():
            cats = item.get("categories", {})
            jobs.append(Job(
                title=item.get("text", ""),
                company="Mistral AI",
                location=cats.get("location", ""),
                department=cats.get("team", ""),
                url=item.get("hostedUrl", ""),
                posted_date=_lever_ts(item.get("createdAt")),
                is_remote="remote" in cats.get("location", "").lower(),
                description=_strip(item.get("descriptionPlain", ""))[:200],
            ))
    except Exception as e:
        logger.warning("Mistral jobs fetch failed: %s", e)
    logger.info("  [Mistral AI] %d jobs", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Scale AI — Greenhouse public API
# ---------------------------------------------------------------------------
def fetch_scale_jobs() -> list[Job]:
    return _greenhouse_jobs("scaleai", "Scale AI")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def collect_jobs() -> list[Job]:
    logger.info("Fetching job listings...")
    all_jobs: list[Job] = []
    for fn in [fetch_openai_jobs, fetch_anthropic_jobs, fetch_deepmind_jobs,
               fetch_mistral_jobs, fetch_scale_jobs]:
        all_jobs.extend(fn())

    # Sort: newest first
    all_jobs.sort(
        key=lambda j: j.posted_date or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    logger.info("Total jobs fetched: %d", len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _lever_ts(ms: Optional[int]) -> Optional[datetime]:
    """Lever timestamps are milliseconds since epoch."""
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except Exception:
        return None


def _iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        s_clean = re.sub(r"\.\d+", "", s)
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.strptime(s_clean[:len(fmt)], fmt)
            except Exception:
                continue
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _strip(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split())
