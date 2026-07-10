"""
Rule-based, multilingual relevance filtering (Section 7.1 of the technical
design guide). No AI/API cost -- pure keyword matching against
config.KEYWORDS.
"""

import config

_KEYWORDS = config.all_keywords()  # precomputed once at import time


def matched_keywords(text):
    """Return the list of configured keywords found in `text` (case-insensitive)."""
    if not text:
        return []
    lowered = text.lower()
    return [kw for kw in _KEYWORDS if kw in lowered]


def is_relevant(item):
    """
    An item is relevant if any configured keyword appears in its title or
    summary. Returns (bool, matched_keywords_list) so callers can store
    which terms triggered the match -- useful for tuning the list later.
    """
    haystack = f"{item.get('title', '')} {item.get('summary', '')}"
    matches = matched_keywords(haystack)
    return (len(matches) > 0, matches)


def filter_items(items):
    """
    Given a list of raw collector items, return only the relevant ones,
    each annotated with a 'matched_keywords' key.
    """
    relevant = []
    for item in items:
        is_rel, matches = is_relevant(item)
        if is_rel:
            item = dict(item)  # don't mutate the caller's dict
            item["matched_keywords"] = matches
            relevant.append(item)
    return relevant
