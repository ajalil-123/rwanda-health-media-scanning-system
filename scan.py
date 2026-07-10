"""
Main entrypoint for the Rwanda Health Media Scanning System.

Usage:
    python scan.py --mode daily
    python scan.py --mode weekly
    python scan.py --mode weekly --end-date 2026-07-06   # re-run for a past week

Each run:
  1. Computes the strict date window for the requested mode (today only for
     daily, trailing 7 days for weekly -- see config.DAILY_WINDOW_DAYS /
     WEEKLY_WINDOW_DAYS).
  2. Collects raw items from all text-based collectors (Google News RSS,
     direct outlet RSS, PubMed).
  3. Drops anything outside the date window.
  4. Filters for health relevance (keyword-based).
  5. Deduplicates near-identical coverage.
  6. Scores and ranks for the Highlights proposal.
  7. Stores everything in SQLite and exports a CSV + Markdown shortlist for
     editorial review.

Radio/TV/YouTube collection is out of scope for this phase (see config.py).
"""

import argparse
import logging
from datetime import datetime, timedelta, timezone

import config
import db
from collectors import google_news, direct_rss, pubmed
from processing import filter_relevance, dedup, highlight_score
import export

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scan")


def compute_window(mode, end_date=None):
    """
    Returns (window_start, window_end) as timezone-aware UTC datetimes,
    strictly scoped to the requested mode -- daily means *that day only*,
    weekly means *that week only* (trailing 7 days ending at end_date),
    not an ever-growing accumulation.
    """
    end = end_date or datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if mode == "daily":
        start = end - timedelta(days=config.DAILY_WINDOW_DAYS)
    elif mode == "weekly":
        start = end - timedelta(days=config.WEEKLY_WINDOW_DAYS)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return start, end


def within_window(item, window_start, window_end):
    """
    Items with an unknown publish date are KEPT rather than silently
    dropped -- some feeds (e.g. PubMed summaries) don't always expose a
    clean date. They're flagged in the shortlist so the editor can judge
    them, rather than the system quietly discarding possibly-relevant
    content because of a parsing gap.
    """
    pub = item.get("published_at")
    if pub is None:
        return True
    return window_start <= pub <= window_end


def run_scan(mode, end_date=None, db_path=None):
    window_start, window_end = compute_window(mode, end_date=end_date)
    started_at = datetime.now(timezone.utc)

    logger.info("Starting %s scan | window: %s to %s", mode, window_start.isoformat(), window_end.isoformat())

    db.init_db(db_path)
    scan_id = db.start_scan(mode, window_start.isoformat(), window_end.isoformat(), started_at.isoformat(), db_path=db_path)

    # 1. Collect ---------------------------------------------------------
    raw_items = []
    raw_items += google_news.collect()
    raw_items += direct_rss.collect()
    raw_items += pubmed.collect(window_start, window_end)
    logger.info("Collected %d raw items across all collectors", len(raw_items))

    # 2. Restrict to the scan's strict date window ------------------------
    windowed_items = [i for i in raw_items if within_window(i, window_start, window_end)]
    logger.info("%d items fall within the %s window", len(windowed_items), mode)

    # 3. Relevance filter --------------------------------------------------
    relevant_items = filter_relevance.filter_items(windowed_items)
    logger.info("%d items are health-relevant", len(relevant_items))

    # 4. Deduplicate ---------------------------------------------------------
    unique_items, duplicate_items = dedup.deduplicate(relevant_items)
    logger.info("%d unique stories after folding %d duplicates", len(unique_items), len(duplicate_items))

    # 5. Score for Highlights -------------------------------------------------
    ranked_items = highlight_score.rank_items(unique_items, now=window_end)

    # 6. Persist ------------------------------------------------------------
    stored_count = 0
    for item in ranked_items:
        item_row = {
            "source_name": item["source_name"],
            "source_category": item["source_category"],
            "title": item["title"],
            "url": item["url"],
            "language": item.get("language"),
            "published_at": item["published_at"].isoformat() if item.get("published_at") else None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "matched_keywords": item.get("matched_keywords", []),
            "snippet": item.get("summary", ""),
        }
        new_id = db.insert_item(item_row, scan_id, db_path=db_path)
        if new_id:
            stored_count += 1

    finished_at = datetime.now(timezone.utc)
    db.finish_scan(
        scan_id, finished_at.isoformat(),
        raw_items=len(raw_items), relevant_items=len(relevant_items), unique_items=len(unique_items),
        db_path=db_path,
    )

    # 7. Export shortlist for editorial review --------------------------------
    scan_info = {
        "mode": mode,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "raw_items_collected": len(raw_items),
        "relevant_items": len(relevant_items),
        "unique_items": len(unique_items),
    }
    date_tag = window_end.strftime("%Y-%m-%d")
    csv_path = export.export_csv(ranked_items, f"output/{mode}_shortlist_{date_tag}.csv")
    md_path = export.export_markdown(ranked_items, f"output/{mode}_shortlist_{date_tag}.md", scan_info)

    logger.info("Scan complete. Shortlist: %s items -> %s / %s", len(ranked_items), csv_path, md_path)
    return {
        "scan_id": scan_id,
        "window_start": window_start,
        "window_end": window_end,
        "ranked_items": ranked_items,
        "csv_path": str(csv_path),
        "md_path": str(md_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Run a daily or weekly RBC health media scan.")
    parser.add_argument("--mode", choices=["daily", "weekly"], required=True)
    parser.add_argument("--end-date", type=str, default=None,
                         help="ISO date (YYYY-MM-DD) to end the window at. Defaults to now. "
                              "Use this to re-run a scan for a past day/week.")
    parser.add_argument("--db-path", type=str, default=None)
    args = parser.parse_args()

    end_date = None
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    run_scan(args.mode, end_date=end_date, db_path=args.db_path)


if __name__ == "__main__":
    main()
