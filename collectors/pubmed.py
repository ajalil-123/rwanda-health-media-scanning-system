"""
PubMed E-utilities collector -- research & journals (Section 6.3 of the
technical design guide). Free, no key required for light use.

Two-step API: esearch (find matching PMIDs within a date range) then
esummary (get titles/dates/journal names for those PMIDs).
"""

import logging

import requests

import config

logger = logging.getLogger(__name__)


def _pubmed_date(dt):
    """PubMed expects YYYY/MM/DD."""
    return dt.strftime("%Y/%m/%d")


def collect(window_start, window_end):
    """
    window_start/window_end: timezone-aware datetimes.
    Returns a flat list of items in the same shape as the other collectors.
    """
    params = {
        "db": "pubmed",
        "term": config.PUBMED_QUERY,
        "datetype": "pdat",
        "mindate": _pubmed_date(window_start),
        "maxdate": _pubmed_date(window_end),
        "retmode": "json",
        "retmax": 200,
    }
    if config.PUBMED_API_KEY:
        params["api_key"] = config.PUBMED_API_KEY

    try:
        resp = requests.get(
            f"{config.PUBMED_BASE_URL}/esearch.fcgi",
            params=params,
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        pmids = resp.json().get("esearchresult", {}).get("idlist", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("PubMed esearch failed: %s", exc)
        return []

    if not pmids:
        logger.info("PubMed query returned no results for this window")
        return []

    try:
        summary_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
        if config.PUBMED_API_KEY:
            summary_params["api_key"] = config.PUBMED_API_KEY
        resp = requests.get(
            f"{config.PUBMED_BASE_URL}/esummary.fcgi",
            params=summary_params,
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
    except Exception as exc:  # noqa: BLE001
        logger.warning("PubMed esummary failed: %s", exc)
        return []

    items = []
    for pmid in result.get("uids", []):
        doc = result.get(pmid, {})
        title = doc.get("title", "").strip()
        if not title:
            continue
        journal = doc.get("fulljournalname") or doc.get("source") or "PubMed"
        items.append({
            "title": title,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "published_at": None,  # esummary date parsing varies; date filtering already applied server-side via mindate/maxdate
            "summary": f"Published in {journal}.",
            "source_name": journal,
            "source_category": "research",
            "language": "en",
        })

    logger.info("PubMed query returned %d items", len(items))
    return items
