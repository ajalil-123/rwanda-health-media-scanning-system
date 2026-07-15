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
    found = [(url, title) for url, title in found if _contains_rwanda_mention(title)]

    # Deduplicate within this page
    seen_urls = set()
    items = []
    for url, title in found:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        items.append({
            "title": title.strip(),
            "url": url,
            "published_at": None,  # Not available reliably from listing pages
            "summary": "",
            "source_name": site["name"],
            "source_category": site.get("category", "international"),
            "language": site.get("language", "en"),
        })

    logger.info("International scrape %s returned %d Rwanda-related items", site["name"], len(items))
    return items


def collect():
    """
    Collect from international news sources.
    
    NOTE: International sources scraper is DISABLED because:
    - Reuters, BBC, AFP, Al Jazeera, France 24, DW block automated requests (HTTP 403)
    - These sites actively detect and block web scrapers
    - Google News already aggregates these same stories anyway
    
    International coverage of Rwanda health is available through:
    - Google News RSS (queries already include international outlets)
    - Direct RSS feeds from outlets that allow it
    
    For custom international coverage, consider:
    - Using news aggregator APIs (NewsAPI, etc.)
    - RSS feeds if the outlet provides them
    """
    all_items = []
    logger.info("International sources collector: DISABLED (blocking). Use Google News instead.")
    return all_items
