"""
Official sources collector -- scrapes Rwanda Ministry of Health, RBC, WHO Rwanda.

These are authoritative sources for official health announcements, policy changes,
and emergency alerts. Getting data directly from these sources (rather than waiting
for news outlets to report them) ensures timeliness and accuracy.

Uses web scraping to extract news/announcement links from their websites.

Publish dates are extracted from HTML where available, providing date/time info
alongside official health announcements.
"""

import logging
from bs4 import BeautifulSoup

import config
from collectors.rss_utils import fetch_url
from collectors.web_scraper import _extract_with_selector, _extract_generic

logger = logging.getLogger(__name__)


def scrape_official_site(site):
    """Scrapes news/announcement section from an official source."""
    try:
        html = fetch_url(site["url"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Official source scrape failed for %s: %s", site["name"], exc)
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse HTML for %s: %s", site["name"], exc)
        return []

    if site.get("link_selector"):
        found = _extract_with_selector(soup, site["link_selector"], site["url"])
        if not found:
            logger.warning(
                "Configured link_selector %r found nothing on %s -- site structure may have changed",
                site["link_selector"], site["name"],
            )
    else:
        # Generic extraction for official sites (usually have structured news sections)
        found = _extract_generic(soup, site["url"], "")

    # Deduplicate
    seen_urls = set()
    items = []
    for url, title, date_element in found:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Try to extract published date
        from collectors.rss_utils import extract_date_from_element
        published_at = extract_date_from_element(date_element) if date_element else None
        # Keep as datetime object, not string

        items.append({
            "title": title.strip(),
            "url": url,
            "published_at": published_at,  # Keep as datetime object
            "summary": "",
            "source_name": site["name"],
            "source_category": site.get("category", "local_online"),
            "language": site.get("language", "en"),
        })

    logger.info("Official source scrape %s returned %d items", site["name"], len(items))
    return items


def collect():
    """Collect from all configured official sources."""
    all_items = []
    for site in config.OFFICIAL_SOURCES:
        all_items += scrape_official_site(site)
    return all_items
