"""
Web scraper collector -- for local news sites that don't have a working
RSS feed (see config.py notes on IGIHE, Panorama, Kigali Today, The
Chronicles). Free, uses only requests + BeautifulSoup (no paid scraping
API).

IMPORTANT, read before enabling a new site:

  1. This uses a GENERIC heuristic by default: it looks at every <a> tag
     on the page, keeps ones that look like article headlines (long
     enough text, not a nav/footer link), and treats them all as
     "possibly today's news." It does NOT know a given site's real
     structure until someone inspects it and configures a specific CSS
     selector in config.SCRAPE_SITES.

  2. The generic heuristic will produce noise (nav links, ads, unrelated
     teasers) on many real sites. Treat its first run against a new site
     as a "does this even find real headlines" check, not a "ready for
     production" check.

  3. To get a precise, low-noise scrape for a specific site: open the
     site in a browser, right-click a headline, choose "Inspect", note
     the CSS class/tag pattern the site uses for headline links (e.g.
     `h2.entry-title a` or `.post-title a`), and set that as
     `link_selector` for that site in config.SCRAPE_SITES. Once set, the
     generic heuristic is skipped entirely for that site.

  4. Published dates are extracted from HTML where possible (from <time>
     elements, .published-date classes, meta tags, or date patterns in
     text). If no date is found, published_at is None, which the scan
     pipeline treats as "keep it, can't rule it out" -- appropriate for
     a homepage listing since it's implicitly recent.

  5. Be a reasonable citizen: this collector sends a descriptive
     User-Agent (config.USER_AGENT) so a site owner can identify and
     block it if they want, and does not parallelize requests across
     sites. Check a site's robots.txt before enabling it here -- this
     collector does not check it automatically.
"""

import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import config
from collectors.rss_utils import fetch_url

logger = logging.getLogger(__name__)

MIN_HEADLINE_LENGTH = 20   # shorter than this is almost always nav/UI text, not a headline
MAX_HEADLINE_LENGTH = 200  # longer than this is almost never a headline either

# Path fragments that are essentially never news article URLs -- used to
# filter obvious non-article links out of the generic heuristic.
_NON_ARTICLE_PATH_HINTS = [
    "/category/", "/tag/", "/tags/", "/author/", "/page/", "/wp-login",
    "/wp-admin", "/about", "/contact", "/privacy", "/subscribe", "/login",
    "/search", "#", "mailto:", "tel:", "javascript:",
]

_GENERIC_HEADLINE_SELECTORS = [
    "article h1 a", "article h2 a", "article h3 a",
    "h1.entry-title a", "h2.entry-title a", "h3.entry-title a",
    ".post-title a", ".entry-title a", ".article-title a", ".headline a",
]


def _looks_like_article_link(url, text, base_domain):
    if not text or not url:
        return False
    text = text.strip()
    if not (MIN_HEADLINE_LENGTH <= len(text) <= MAX_HEADLINE_LENGTH):
        return False
    lowered_url = url.lower()
    if any(hint in lowered_url for hint in _NON_ARTICLE_PATH_HINTS):
        return False
    # Keep only links to the same site -- avoids picking up ad networks,
    # social share links, etc. Uses an exact host match (not "contains"),
    # since substring matching would wrongly let "external-ads.example.com"
    # through as if it were "example.com".
    link_domain = urlparse(url).netloc
    if base_domain and link_domain and link_domain != base_domain:
        return False
    return True


def _extract_with_selector(soup, selector, base_url):
    items = []
    for a in soup.select(selector):
        href = a.get("href")
        text = a.get_text(strip=True)
        if not href or not text:
            continue
        
        # Try to find date info nearby the link
        # Look in parent containers (article, div, li, etc.)
        date_element = None
        for parent in a.parents:
            # Stop at body level
            if parent.name == "body":
                break
            # Try to find date in this parent
            from collectors.rss_utils import extract_date_from_element
            test_date = extract_date_from_element(parent)
            if test_date:
                date_element = parent
                break
        
        items.append((urljoin(base_url, href), text, date_element))
    return items


def _extract_generic(soup, base_url, base_domain):
    """Fallback used when a site has no configured link_selector. Tries
    the common headline-selector patterns first (low noise if they
    happen to match), and if none of those find anything, falls back to
    scanning every link on the page and filtering by heuristic."""
    for selector in _GENERIC_HEADLINE_SELECTORS:
        found = _extract_with_selector(soup, selector, base_url)
        if found:
            return found

    # Last resort: every link on the page, filtered.
    items = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        text = a.get_text(strip=True)
        if _looks_like_article_link(href, text, base_domain):
            # Try to find date in parent container
            date_element = None
            for parent in a.parents:
                if parent.name == "body":
                    break
                from collectors.rss_utils import extract_date_from_element
                test_date = extract_date_from_element(parent)
                if test_date:
                    date_element = parent
                    break
            items.append((href, text, date_element))
    return items


def scrape_site(site):
    """Scrapes one configured site. Returns a list of raw item dicts.
    Never raises -- logs a warning and returns [] on any failure, so one
    broken site doesn't stop the others."""
    try:
        html = fetch_url(site["url"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Web scrape failed for %s: %s", site["name"], exc)
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse HTML for %s: %s", site["name"], exc)
        return []

    base_domain = urlparse(site["url"]).netloc

    if site.get("link_selector"):
        found = _extract_with_selector(soup, site["link_selector"], site["url"])
        if not found:
            logger.warning(
                "Configured link_selector %r found nothing on %s -- the site's "
                "HTML structure may have changed. Re-check the selector.",
                site["link_selector"], site["name"],
            )
    else:
        found = _extract_generic(soup, site["url"], base_domain)
        logger.info(
            "%s has no configured link_selector -- used the generic heuristic "
            "(%d candidate links found). Inspect the results; if noisy, add a "
            "specific link_selector in config.SCRAPE_SITES.",
            site["name"], len(found),
        )

    # De-duplicate within this single page (the same headline often links
    # from multiple spots -- a thumbnail and a title, for instance).
    seen_urls = set()
    items = []
    for url, title, date_element in found:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Try to extract published date from the article element
        from collectors.rss_utils import extract_date_from_element
        published_at = extract_date_from_element(date_element) if date_element else None
        # extract_date_from_element returns a datetime object, which is what we need

        items.append({
            "title": re.sub(r"\s+", " ", title).strip(),
            "url": url,
            "published_at": published_at,  # Keep as datetime object, not string
            "summary": "",
            "source_name": site["name"],
            "source_category": site.get("category", "local_online"),
            "language": site.get("language", "en"),
        })

    logger.info("Web scrape %s returned %d candidate items", site["name"], len(items))
    return items


def collect():
    all_items = []
    for site in config.SCRAPE_SITES:
        all_items += scrape_site(site)
    return all_items
