"""
Direct RSS collector for priority outlets (config.DIRECT_RSS_FEEDS).

Preferred over Google News for these outlets specifically because it's
faster, fresher, and gives the real publisher URL instead of a Google
redirect. Add confirmed feeds to config.DIRECT_RSS_FEEDS as they're
verified during the source audit.
"""

import logging

import config
from collectors.rss_utils import fetch_url, parse_feed

logger = logging.getLogger(__name__)


def collect():
    all_items = []
    for source in config.DIRECT_RSS_FEEDS:
        try:
            xml_text = fetch_url(source["url"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Direct RSS feed failed: %s (%s)", source["name"], exc)
            continue

        parsed = parse_feed(xml_text)
        for item in parsed:
            all_items.append({
                "title": item["title"],
                "url": item["url"],
                "published_at": item["published_at"],
                "summary": item.get("summary") or "",
                "source_name": source["name"],
                "source_category": source["category"],
                "language": source["language"],
            })
        logger.info("Direct RSS %s returned %d items", source["name"], len(parsed))

    return all_items
