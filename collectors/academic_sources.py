"""
Academic & Research sources collector -- Google Scholar, ResearchGate, SSRN, arXiv.

Complements PubMed with broader academic coverage: policy papers, working papers,
preprints, and research from sources beyond traditional journals.

WARNING: These sites have varying policies on automation. Use respectfully:
- arXiv: Allows reasonable automated requests
- ResearchGate, SSRN: Allow scraping but prefer respectful rates
- Google Scholar: Actively blocks scrapers; best effort only

If a source blocks requests consistently, it will be logged and skipped.
"""

import logging
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urljoin

import config
from collectors.rss_utils import fetch_url

logger = logging.getLogger(__name__)


def scrape_google_scholar(query="Rwanda health"):
    """
    Attempt to scrape Google Scholar for a query.
    WARNING: Google Scholar blocks scrapers aggressively.
    This is a best-effort attempt that will likely fail or return limited results.
    """
    url = f"https://scholar.google.com/scholar?q={query}"
    logger.info("Google Scholar search: %s (note: Google blocks scrapers)", query)

    try:
        # fetch_url doesn't accept user_agent parameter, just use default
        html = fetch_url(url)
    except Exception as exc:
        logger.warning("Google Scholar scrape failed (expected due to blocking): %s", exc)
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.warning("Could not parse Google Scholar HTML: %s", exc)
        return []

    # Google Scholar's structure is anti-scraper-oriented, but try the common pattern
    items = []
    for result in soup.find_all("div", class_="gs_ri"):
        title_elem = result.find("h3")
        if not title_elem:
            continue
        a_elem = title_elem.find("a")
        if not a_elem:
            continue
        title = a_elem.get_text(strip=True)
        url = a_elem.get("href", "")
        if not url:
            continue

        items.append({
            "title": title,
            "url": url,
            "published_at": None,
            "summary": "",
            "source_name": "Google Scholar",
            "source_category": "research",
            "language": "en",
        })

    logger.info("Google Scholar returned %d items (likely incomplete due to blocking)", len(items))
    return items


def scrape_researchgate(query="Rwanda health"):
    """Scrape ResearchGate for research papers on Rwanda health."""
    search_url = f"https://www.researchgate.net/search?q={query}"
    logger.info("ResearchGate search: %s", query)

    try:
        html = fetch_url(search_url)
    except Exception as exc:
        logger.warning("ResearchGate scrape failed: %s", exc)
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.warning("Could not parse ResearchGate HTML: %s", exc)
        return []

    items = []
    for publication in soup.find_all("div", class_="publication-item"):
        title_elem = publication.find("h4")
        if not title_elem:
            continue
        a_elem = title_elem.find("a")
        if not a_elem:
            continue
        title = a_elem.get_text(strip=True)
        url = a_elem.get("href", "")
        if not url:
            continue

        items.append({
            "title": title,
            "url": urljoin("https://www.researchgate.net", url),
            "published_at": None,
            "summary": "",
            "source_name": "ResearchGate",
            "source_category": "research",
            "language": "en",
        })

    logger.info("ResearchGate returned %d items", len(items))
    return items


def scrape_ssrn(query="Rwanda health"):
    """Scrape SSRN for working papers on Rwanda health."""
    search_url = f"https://papers.ssrn.com/sol3/results.cfm?nflag=1&q={query}"
    logger.info("SSRN search: %s", query)

    try:
        html = fetch_url(search_url)
    except Exception as exc:
        logger.warning("SSRN scrape failed: %s", exc)
        return []

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.warning("Could not parse SSRN HTML: %s", exc)
        return []

    items = []
    for paper in soup.find_all("div", class_="paper-header"):
        title_elem = paper.find("a")
        if not title_elem:
            continue
        title = title_elem.get_text(strip=True)
        url = title_elem.get("href", "")
        if not url or "ssrn" not in url:
            continue

        items.append({
            "title": title,
            "url": urljoin("https://papers.ssrn.com", url),
            "published_at": None,
            "summary": "",
            "source_name": "SSRN",
            "source_category": "research",
            "language": "en",
        })

    logger.info("SSRN returned %d items", len(items))
    return items


def scrape_arxiv(query="Rwanda health"):
    """
    Query arXiv API for papers on Rwanda health.
    arXiv has a free API that doesn't require scraping.
    """
    import urllib.request
    import urllib.parse
    import json

    logger.info("arXiv search: %s", query)
    # Properly encode the query to handle spaces and special characters
    encoded_query = urllib.parse.quote(query)
    search_url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending"

    try:
        with urllib.request.urlopen(search_url, timeout=5) as response:
            data = response.read().decode("utf-8")
    except Exception as exc:
        logger.warning("arXiv API request failed: %s", exc)
        return []

    items = []
    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title_elem = entry.find("atom:title", ns)
            id_elem = entry.find("atom:id", ns)
            if title_elem is None or id_elem is None:
                continue

            title = title_elem.text.strip() if title_elem.text else ""
            arxiv_id = id_elem.text.replace("http://arxiv.org/abs/", "").strip()
            url = f"https://arxiv.org/abs/{arxiv_id}"

            items.append({
                "title": title,
                "url": url,
                "published_at": None,
                "summary": "",
                "source_name": "arXiv",
                "source_category": "research",
                "language": "en",
            })
    except Exception as exc:
        logger.warning("Failed to parse arXiv results: %s", exc)

    logger.info("arXiv returned %d items", len(items))
    return items


def collect():
    """Collect from all configured academic/research sources."""
    all_items = []

    for source in config.RESEARCH_SOURCES:
        if source["source"] == "google_scholar":
            all_items += scrape_google_scholar(source.get("query", "Rwanda health"))
        elif source["source"] == "researchgate":
            all_items += scrape_researchgate(source.get("query", "Rwanda health"))
        elif source["source"] == "ssrn":
            all_items += scrape_ssrn(source.get("query", "Rwanda health"))
        elif source["source"] == "arxiv":
            all_items += scrape_arxiv(source.get("query", "Rwanda health"))

    return all_items
