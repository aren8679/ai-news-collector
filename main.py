"""
AI News Collector — main entry point.

Usage:
    python main.py                  # collect & process & generate report
    python main.py --no-summary     # skip processing (raw RSS only, for debugging)
    python main.py --hours 48       # collect articles from the last 48 hours
    python main.py --feeds overseas # only collect from a specific category
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup — must come before local imports that use logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
import config as cfg
from collector import collect_articles
from summarizer import summarize_articles
from reporter import generate_report
from dashboard import generate_dashboard
from job_collector import collect_jobs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI News Collector — fetch, summarize, and report AI news."
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip RSS-based processing (raw output only, for debugging).",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help=f"Collect articles published within N hours (default: {cfg.FETCH_HOURS}).",
    )
    parser.add_argument(
        "--feeds",
        choices=["all", "overseas", "official_blog", "japan"],
        default="all",
        help="Which feed category to collect (default: all).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Directory to save reports (default: {cfg.OUTPUT_DIR}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Apply CLI overrides to config globals
    if args.hours is not None:
        cfg.FETCH_HOURS = args.hours
    if args.output_dir is not None:
        cfg.OUTPUT_DIR = args.output_dir

    # ---- 1. Choose feeds ----
    feeds = cfg.RSS_FEEDS
    if args.feeds != "all":
        feeds = [f for f in feeds if f.category == args.feeds]
        logger.info("Filtering feeds to category: %s (%d feeds)", args.feeds, len(feeds))

    if not feeds:
        logger.error("No feeds selected. Exiting.")
        sys.exit(1)

    # ---- 2. Collect articles ----
    logger.info("=== Step 1/3: Collecting articles (last %dh) ===", cfg.FETCH_HOURS)
    articles = collect_articles(feeds)

    if not articles:
        logger.warning("No articles found. Nothing to report.")
        sys.exit(0)

    # ---- 3. Process (format summaries + detect topics) ----
    if args.no_summary:
        logger.info("=== Step 2/3: Skipping processing (--no-summary) ===")
    else:
        logger.info("=== Step 2/3: Processing %d article(s) ===", len(articles))
        articles = summarize_articles(articles)

    # ---- 4. Collect job listings ----
    logger.info("=== Step 3/4: Fetching job listings ===")
    jobs = collect_jobs()

    # ---- 5. Generate report + dashboard ----
    logger.info("=== Step 4/4: Generating Markdown report & HTML dashboard ===")
    report_path    = generate_report(articles)
    dashboard_path = generate_dashboard(articles, jobs)

    logger.info("")
    logger.info("Done!")
    logger.info("  Markdown : %s", report_path)
    logger.info("  Dashboard: %s", dashboard_path)
    logger.info("  記事: %d件 / 求人: %d件", len(articles), len(jobs))


if __name__ == "__main__":
    main()
