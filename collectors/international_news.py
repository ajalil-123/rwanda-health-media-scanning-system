"""
International news sources collector -- scrapes major outlets covering Rwanda.

Uses the same web scraping approach as collectors/web_scraper.py but extended
for international sites (Reuters, BBC, AFP, Al Jazeera, France 24, DW, Africanews).

Most international outlets don't have Rwanda-specific RSS feeds, so this collector
scrapes their Africa/news sections looking for Rwanda-related stories.

After scraping, a second keyword filter ensures only Rwanda-focused articles are kept.

Publish dates are extracted from HTML where available (time elements, date classes,
meta tags, or text patterns). This ensures international news has date/time info
just like RSS feeds do.
"""

import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin

import config
from collectors.rss_utils import fetch_url
from collectors.web_scraper import _extract_with_selector, _extract_generic, _looks_like_article_link

logger = logging.getLogger(__name__)

RWANDA_KEYWORDS = ["Rwanda", "Rwandan", "Kigali", "RBC"]

def _contains_rwanda_mention(text):
    """Quick filter to ensure the headline actually mentions Rwanda,
    not just a generic Africa article."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in RWANDA_KEYWORDS)


def scrape_international_site(site):
    """Scrapes one international source and filters for Rwanda mentions."""
    try:
        html = fetch_url(site["url"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("International scrape failed for %s: %s", site["name"], exc)
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse HTML for %s: %s", site["name"], exc)
        return []

    if site.get("link_selector"):
        found = _extract_with_selector(soup, site["link_selector"], site["url"])
    else:
        # Generic extraction for international sites
        found = _extract_generic(soup, site["url"], "")

    # Filter for Rwanda mentions
    found = [(url, title, date_elem) for url, title, date_elem in found if _contains_rwanda_mention(title)]

    # Deduplicate within this page
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
            "source_category": site.get("category", "international"),
            "language": site.get("language", "en"),
        })

    logger.info("International scrape %s returned %d Rwanda-related items", site["name"], len(items))
    return items


def collect():
    """Collect from all configured international sources."""
    all_items = []
    for site in config.INTERNATIONAL_SOURCES:
        all_items += scrape_international_site(site)
    return all_items
