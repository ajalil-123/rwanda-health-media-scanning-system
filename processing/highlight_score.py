"""
Transparent highlight-ranking heuristic (Section 7.4 of the technical
design guide). No AI cost -- a simple, explainable weighted score so the
editor can see *why* something was proposed as a highlight, and override it.
"""

from datetime import datetime, timezone

WEIGHT_OUTLET_COUNT = 3.0    # how many outlets covered the same story
WEIGHT_KEYWORD_COUNT = 1.0   # how many priority keywords matched (topic signal)
WEIGHT_RECENCY = 2.0         # newer items score higher


def _recency_score(published_at, now=None):
    if not published_at:
        return 0.0
    now = now or datetime.now(timezone.utc)
    age_hours = max((now - published_at).total_seconds() / 3600, 0)
    # Full score if <6h old, decaying to 0 by 7 days (168h)
    return max(0.0, 1 - (age_hours / 168))


def score_item(item, now=None):
    outlet_count = len(item.get("covered_by", [item.get("source_name", "")]))
    keyword_count = len(item.get("matched_keywords", []))
    recency = _recency_score(item.get("published_at"), now=now)

    score = (
        WEIGHT_OUTLET_COUNT * outlet_count
        + WEIGHT_KEYWORD_COUNT * keyword_count
        + WEIGHT_RECENCY * recency
    )
    return round(score, 2)


def rank_items(items, now=None):
    """Return items sorted by highlight_score descending, each annotated
    with its score. Does not mutate the input list."""
    scored = []
    for item in items:
        item = dict(item)
        item["highlight_score"] = score_item(item, now=now)
        scored.append(item)
    return sorted(scored, key=lambda i: i["highlight_score"], reverse=True)
