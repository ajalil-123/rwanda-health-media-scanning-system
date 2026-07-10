"""
Main entrypoint for the Rwanda Health Media Scanning System.

Usage:
    python scan.py --mode daily                     # today
    python scan.py --mode daily --date 2026-07-06    # a specific past day
    python scan.py --mode weekly                     # the 7 days ending today
    python scan.py --mode weekly --date 2026-07-06    # the 7 days ending 2026-07-06

Each run:
  1. Computes the strict, calendar-aligned date window for the requested
     mode and date: daily means that one calendar day (00:00:00 to
     23:59:59 on that date), weekly means the 7 calendar days ending on
     that date (see config.DAILY_WINDOW_DAYS / WEEKLY_WINDOW_DAYS). If no
     date is given, today (UTC) is used. Running the same --mode/--date
     combination twice always computes the same window -- the result
     doesn't depend on what time of day you happen to run it.
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
from datetime import date, datetime, timedelta, timezone

import config
import db
from collectors import google_news, direct_rss, pubmed, web_scraper
from processing import filter_relevance, dedup, highlight_score
import export

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scan")


def compute_window(mode, target_date=None, start_date=None):
    """
    Returns (window_start, window_end) as timezone-aware UTC datetimes.

      - daily:  that single calendar day, 00:00:00 to 23:59:59 UTC.
                `target_date` is the day to scan; `start_date` is ignored.
      - weekly: if `start_date` is given, scans that EXACT custom period
                (start_date 00:00:00 to target_date 23:59:59) -- lets a
                user pick any period, not just a fixed 7 days. If
                `start_date` is omitted, falls back to the default
                config.WEEKLY_WINDOW_DAYS calendar days ending on
                target_date.

    target_date: a `date` (or `datetime`, only its date portion is used)
    -- the day to scan for (daily) or the day the period should end on
    (weekly). Defaults to today (UTC) if not given.

    start_date: a `date` (or `datetime`) -- optional explicit start of a
    custom weekly period. Must not be after target_date.
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()
    if isinstance(start_date, datetime):
        start_date = start_date.date()

    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1) - timedelta(seconds=1)  # 23:59:59 that day, inclusive

    if mode == "daily":
        return day_start, day_end
    elif mode == "weekly":
        if start_date is not None:
            if start_date > target_date:
                raise ValueError(f"start_date ({start_date}) must not be after target_date ({target_date})")
            week_start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
        else:
            week_start = day_start - timedelta(days=config.WEEKLY_WINDOW_DAYS - 1)
        return week_start, day_end
    else:
        raise ValueError(f"Unknown mode: {mode}")


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


def run_scan(mode, target_date=None, start_date=None, db_path=None):
    window_start, window_end = compute_window(mode, target_date=target_date, start_date=start_date)
    started_at = datetime.now(timezone.utc)

    logger.info("Starting %s scan | window: %s to %s", mode, window_start.isoformat(), window_end.isoformat())

    db.init_db(db_path)
    scan_id = db.start_scan(mode, window_start.isoformat(), window_end.isoformat(), started_at.isoformat(), db_path=db_path)

    # 1. Collect, tracking each collector separately for diagnostics ---------
    collector_counts = {}

    def _run_collector(name, fn):
        try:
            items = fn()
        except Exception as exc:  # noqa: BLE001 -- a collector-level crash shouldn't kill the scan
            logger.warning("Collector %s raised an unexpected error: %s", name, exc)
            items = []
        collector_counts[name] = len(items)
        logger.info("Collector %-15s -> %d raw items", name, len(items))
        return items

    raw_items = []
    raw_items += _run_collector("google_news", google_news.collect)
    raw_items += _run_collector("direct_rss", direct_rss.collect)
    raw_items += _run_collector("web_scraper", web_scraper.collect)
    raw_items += _run_collector("pubmed", lambda: pubmed.collect(window_start, window_end))

    logger.info("Collected %d raw items across all collectors", len(raw_items))
    if len(raw_items) == 0:
        logger.warning(
            "Zero raw items from every collector -- this usually means a network/access "
            "problem (blocked outbound requests, firewall, or a proxy), not a lack of news. "
            "Check the WARNING lines above from each collector for the specific error."
        )
    else:
        sample_titles = [f"  - [{i['source_category']}/{i['source_name']}] {i['title'][:80]}" for i in raw_items[:5]]
        logger.info("Sample of raw items collected:\n%s", "\n".join(sample_titles))

    # 2. Restrict to the scan's strict date window ------------------------
    windowed_items = [i for i in raw_items if within_window(i, window_start, window_end)]
    logger.info("%d items fall within the %s window", len(windowed_items), mode)
    if len(raw_items) > 0 and len(windowed_items) == 0:
        logger.warning(
            "All %d collected items fell OUTSIDE the requested window (%s to %s). "
            "This commonly happens with Google News RSS, which can return items several "
            "days old rather than same-day news -- try --mode weekly, or a wider date range, "
            "to confirm the collectors themselves are working.",
            len(raw_items), window_start.date(), window_end.date(),
        )

    # 3. Relevance filter --------------------------------------------------
    relevant_items = filter_relevance.filter_items(windowed_items)
    logger.info("%d items are health-relevant", len(relevant_items))
    if len(windowed_items) > 0 and len(relevant_items) == 0:
        logger.warning(
            "%d items were in the window but NONE matched the health keyword list "
            "(config.KEYWORDS). Either it was a quiet news day for health topics, or the "
            "keyword list needs broadening -- check the sample titles logged above.",
            len(windowed_items),
        )

    # 4. Deduplicate ---------------------------------------------------------
    unique_items, duplicate_items = dedup.deduplicate(relevant_items)
    logger.info("%d unique stories after folding %d duplicates", len(unique_items), len(duplicate_items))

    # Per-category breakdown -- makes it obvious if e.g. local_online is
    # empty while international/research have items, or vice versa.
    category_counts = {}
    for item in unique_items:
        category_counts[item["source_category"]] = category_counts.get(item["source_category"], 0) + 1
    logger.info("By section: %s", category_counts or "(none)")

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
            "highlight_score": item.get("highlight_score"),
            "covered_by": item.get("covered_by", []),
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
        "diagnostics": {
            "collector_counts": collector_counts,
            "raw_items": len(raw_items),
            "windowed_items": len(windowed_items),
            "relevant_items": len(relevant_items),
            "unique_items": len(unique_items),
            "category_counts": category_counts,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run a daily or weekly Rwanda Health Media scan for a specific date.")
    parser.add_argument("--mode", choices=["daily", "weekly"], required=True)
    parser.add_argument("--date", type=str, default=None,
                         help="ISO date (YYYY-MM-DD) to scan for. For --mode daily, this is the "
                              "exact calendar day scanned. For --mode weekly, this is the day the "
                              "period ends on (inclusive) -- combine with --start-date for a custom "
                              "period, or omit --start-date for the default 7-day period. Defaults "
                              "to today (UTC) if not given.")
    parser.add_argument("--start-date", type=str, default=None,
                         help="ISO date (YYYY-MM-DD). Only used with --mode weekly: the exact start "
                              "of a custom period, paired with --date as the end. Lets you scan any "
                              "period, not just 7 days. Ignored for --mode daily.")
    parser.add_argument("--db-path", type=str, default=None)
    args = parser.parse_args()

    target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else None

    run_scan(args.mode, target_date=target_date, start_date=start_date, db_path=args.db_path)


if __name__ == "__main__":
    main()
