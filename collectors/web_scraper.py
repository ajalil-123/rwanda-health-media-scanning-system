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

  4. Publish dates are recovered in TWO cheap-to-expensive steps so the
     scan's strict date window can be applied to scraped items:
       a. From the article URL, if it embeds a date (e.g. /2026/07/14/slug).
          Free -- no extra request.
       b. For headlines that (a) didn't date AND that match the health
          keyword filter, by fetching the article page and reading its
          published date (<time> tags, date CSS classes, OG/schema meta).
          This costs one HTTP request per article, so it runs ONLY on
          keyword-matching headlines (there's no point spending a request
          on a story we're about to discard) and is bounded by a count
          cap, a wall-clock budget, and a short per-request timeout so it
          can never blow Render's worker timeout. See
          _enrich_dates_from_articles below and DATE_FILTER_FIX.md.
     Anything still undated after both steps is left with published_at=None,
     which -- under the default strict policy (config.KEEP_UNDATED_ITEMS =
     False) -- means the scan's date window drops it rather than letting it
     leak in regardless of the requested date.

  5. Be a reasonable citizen: this collector sends a descriptive
     User-Agent (config.USER_AGENT) so a site owner can identify and
     block it if they want, and does not parallelize requests across
     sites. Check a site's robots.txt before enabling it here -- this
     collector does not check it automatically.
"""

import logging
import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import config
from collectors.rss_utils import fetch_url, extract_date_from_url, extract_date_from_element
from processing.filter_relevance import is_relevant

logger = logging.getLogger(__name__)

MIN_HEADLINE_LENGTH = 20   # shorter than this is almost always nav/UI text, not a headline
MAX_HEADLINE_LENGTH = 200  # longer than this is almost never a headline either

# --- Optional article date-fetch settings (step 4b above). --------------
# Read from config.py if present, else these defaults. They are deliberately
# conservative for the Render free tier (30s worker timeout); raise them if
# you run on a paid plan or via cron where the timeout doesn't apply.
_ARTICLE_FETCH_DEFAULTS = {
    "ARTICLE_DATE_FETCH_ENABLED": True,   # master on/off switch
    "ARTICLE_DATE_FETCH_MAX": 20,         # hard cap on article fetches per scan
    "ARTICLE_DATE_FETCH_BUDGET_SECONDS": 10,  # wall-clock ceiling across all article fetches
    "ARTICLE_DATE_FETCH_TIMEOUT_SECONDS": 5,  # per-request timeout (shorter than the feed timeout)
}

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


def _cfg(name):
    """Read an optional ARTICLE_DATE_FETCH_* setting from config.py, falling
    back to the conservative default if it isn't defined -- so this works
    whether or not those (optional) settings have been added to config.py."""
    return getattr(config, name, _ARTICLE_FETCH_DEFAULTS[name])


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
        items.append((urljoin(base_url, href), text))
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
            items.append((href, text))
    return items


def scrape_site(site):
    """Scrapes one configured site. Returns a list of raw item dicts, each
    with a publish date recovered from the URL where present (see step 4a in
    the module docstring). Article-page date recovery (step 4b) happens later,
    once, in collect() -- so a direct scrape_site() call does no article
    fetching. Never raises -- logs a warning and returns [] on any failure,
    so one broken site doesn't stop the others."""
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
    url_undated = 0
    for url, title in found:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Step 4a: recover a date from the article URL where present (free).
        published_at = extract_date_from_url(url)
        if published_at is None:
            url_undated += 1

        items.append({
            "title": re.sub(r"\s+", " ", title).strip(),
            "url": url,
            "published_at": published_at,
            "summary": "",
            "source_name": site["name"],
            "source_category": site.get("category", "local_online"),
            "language": site.get("language", "en"),
        })

    if items and url_undated:
        logger.info(
            "Web scrape %s: %d of %d candidate items had no date in their URL "
            "(a date may still be recovered from the article page for "
            "health-matching headlines; see collect()).",
            site["name"], url_undated, len(items),
        )

    logger.info("Web scrape %s returned %d candidate items", site["name"], len(items))
    return items


def _enrich_dates_from_articles(items):
    """Second, more expensive date-recovery pass (step 4b in the module
    docstring). For candidate items that STILL have no date after URL
    parsing, fetch the article page and read its published date.

    Guardrails, so this is safe on Render's 30s worker timeout:
      - Runs ONLY on headlines whose title matches the health keyword filter
        -- no request is spent on a story that would be discarded anyway, so
        on a typical day this is a handful of fetches, not hundreds.
      - Stops after config.ARTICLE_DATE_FETCH_MAX fetches (count cap).
      - Stops after config.ARTICLE_DATE_FETCH_BUDGET_SECONDS of wall-clock
        (time cap), so a run of slow pages can't accumulate past the budget.
      - Each fetch uses config.ARTICLE_DATE_FETCH_TIMEOUT_SECONDS (shorter
        than the feed timeout), so a single hung page is bounded too.
      - Can be turned off entirely with config.ARTICLE_DATE_FETCH_ENABLED.

    Mutates `items` in place; returns the number of article pages fetched.
    Items whose date still can't be found are left as published_at=None and
    fall to the scan's strict window rule (dropped unless KEEP_UNDATED_ITEMS).
    """
    if not _cfg("ARTICLE_DATE_FETCH_ENABLED"):
        return 0

    max_fetches = _cfg("ARTICLE_DATE_FETCH_MAX")
    budget_s = _cfg("ARTICLE_DATE_FETCH_BUDGET_SECONDS")
    per_req_timeout = _cfg("ARTICLE_DATE_FETCH_TIMEOUT_SECONDS")

    fetched = 0
    recovered = 0
    started = time.monotonic()

    for item in items:
        if item.get("published_at") is not None:
            continue  # already dated (from its URL) -- no request needed
        if fetched >= max_fetches:
            logger.info(
                "Article date-fetch cap (%d) reached -- remaining undated items left as-is "
                "(they'll be dropped by the strict date window unless KEEP_UNDATED_ITEMS).",
                max_fetches,
            )
            break
        if (time.monotonic() - started) > budget_s:
            logger.info(
                "Article date-fetch time budget (%ss) spent -- remaining undated items left as-is.",
                budget_s,
            )
            break
        # Only spend a request on stories that actually look health-related.
        if not is_relevant(item)[0]:
            continue
        try:
            html = fetch_url(item["url"], timeout=per_req_timeout)
        except Exception as exc:  # noqa: BLE001 -- one bad article must not stop the rest
            logger.warning("Article date-fetch failed for %s: %s", item["url"], exc)
            fetched += 1  # a failed attempt still spends part of the budget
            continue
        fetched += 1
        dt = extract_date_from_element(html)
        if dt is not None:
            item["published_at"] = dt
            recovered += 1

    if fetched:
        logger.info(
            "Article date-fetch: fetched %d article page(s), recovered a publish date for %d.",
            fetched, recovered,
        )
    return fetched


def collect():
    all_items = []
    for site in config.SCRAPE_SITES:
        all_items += scrape_site(site)
    _enrich_dates_from_articles(all_items)
    return all_items
