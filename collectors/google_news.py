"""
Google News RSS collector.

Free, keyless, broad discovery -- catches health-related coverage of Rwanda
across the wider media landscape, not just the fixed outlet list. See
Section 6.1 of the technical design guide for the known limitations of this
endpoint (roughly 100-item cap per query, redirect links, skews a few days
old rather than breaking news).
"""

import logging
import re
import unicodedata

import config
from collectors.rss_utils import fetch_url, parse_feed

logger = logging.getLogger(__name__)

BASE_URL = "https://news.google.com/rss/search"

# Outlets known to be Rwandan/local -- used to classify Google News results
# into the right report section. Anything not matched here is treated as
# international. Extend this list as new local outlets are confirmed.
#
# Matching runs on a NORMALISED form of the name (see _normalize): accents
# stripped, spacing and punctuation removed, lowercased. That's deliberate --
# Google News reports these names with real spacing/casing ("KT Press",
# "Kigali Today", "Le Canapé"), and the earlier raw-substring check looked
# for e.g. "ktpress" inside "kt press" and silently failed, mislabelling KT
# Press as International. Write hints in readable form; normalisation makes
# spacing/accents irrelevant on both sides.
_LOCAL_OUTLET_HINTS = [
    "new times", "kt press", "igihe", "taarifa", "panorama", "kigali today",
    "the chronicles", "rwanda today", "umuseke", "imvaho", "umuryango",
    "le canape", "nouvelle releve", "rwanda news agency", "inyarwanda",
    "pureafricanews", "topafricanews", "allafrica",
]


def _normalize(text):
    """Lowercase, strip accents, and remove every non-alphanumeric character,
    so outlet-name matching survives differences in spacing, punctuation and
    accents. 'KT Press' -> 'ktpress'; 'Le Canapé' -> 'lecanape'."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", without_accents.lower())


_NORMALIZED_LOCAL_HINTS = [_normalize(hint) for hint in _LOCAL_OUTLET_HINTS]


def _strip_source_suffix(title, source_name):
    """Google News titles are often 'Article Title - Publisher Name'. Since
    we already have the publisher from the <source> tag, strip the
    redundant suffix so titles compare cleanly during deduplication."""
    if not title or not source_name:
        return title
    suffix = f" - {source_name}"
    if title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title


def _classify_category(source_name):
    if not source_name:
        return "local_online"  # unknown publisher -- default; editor can correct in review
    normalized = _normalize(source_name)
    if any(hint and hint in normalized for hint in _NORMALIZED_LOCAL_HINTS):
        return "local_online"
    return "international"


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
            source_name = item.get("source_name") or "Google News (unattributed)"
            from collectors.rss_utils import strip_html_tags
            all_items.append({
                "title": _strip_source_suffix(item["title"], item.get("source_name")),
                "url": item["url"],
                "published_at": item["published_at"],
                "summary": strip_html_tags(item.get("summary") or ""),
                "source_name": source_name,
                "source_category": _classify_category(item.get("source_name")),
                "language": q["hl"].split("-")[0],
            })
        logger.info("Google News query %r returned %d items", q["query"], len(parsed))

    return all_items
