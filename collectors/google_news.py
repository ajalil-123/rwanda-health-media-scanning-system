"""
Google News RSS collector.

Free, keyless, broad discovery -- catches health-related coverage of Rwanda
across the wider media landscape, not just the fixed outlet list. See
Section 6.1 of the technical design guide for the known limitations of this
endpoint (roughly 100-item cap per query, redirect links, skews a few days
old rather than breaking news).
"""

import logging

import config
from collectors.rss_utils import fetch_url, parse_feed

logger = logging.getLogger(__name__)

BASE_URL = "https://news.google.com/rss/search"


def collect():
    """
    Runs every query in config.GOOGLE_NEWS_QUERIES and returns a flat list
    of raw items: {title, url, published_at, summary, source_name, source_category, language}

    Any single query failing (network error, bad response) is logged and
    skipped -- it does not stop the other queries or the rest of the scan.
    """
    all_items = []
    for q in config.GOOGLE_NEWS_QUERIES:
        params = {"q": q["query"], "hl": q["hl"], "gl": q["gl"], "ceid": q["ceid"]}
        try:
            xml_text = fetch_url(BASE_URL, params=params)
        except Exception as exc:  # noqa: BLE001 -- deliberately broad, this is a collector boundary
            logger.warning("Google News query failed: %r (%s)", q["query"], exc)
            continue

        parsed = parse_feed(xml_text)
        for item in parsed:
            all_items.append({
                "title": item["title"],
                "url": item["url"],
                "published_at": item["published_at"],
                "summary": item.get("summary") or "",
                "source_name": "Google News",
                "source_category": "local_online",  # refined later by classify.py using the underlying source
                "language": q["hl"].split("-")[0],
            })
        logger.info("Google News query %r returned %d items", q["query"], len(parsed))

    return all_items
