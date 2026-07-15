"""
Rule-based, multilingual relevance filtering (Section 7.1 of the technical
design guide). No AI/API cost -- pure keyword matching against
config.KEYWORDS.

Uses word boundary matching to avoid false positives:
- "hospital" matches "hospital", "hospitals" but NOT "hospitality"
- Keyword must be a complete word (including common English plurals), not a substring
"""

import re
import config

_KEYWORDS = config.all_keywords()  # precomputed once at import time


def matched_keywords(text):
    """
    Return the list of configured keywords found in `text` (case-insensitive).
    Uses word boundaries to avoid false positives:
    - "hospital" matches "hospital" or "hospitals" but NOT "hospitality"
    - Keyword must be a complete word, optionally with plural 's' or 'es'
    """
    if not text:
        return []
    lowered = text.lower()
    matched = []
    for kw in _KEYWORDS:
        # Build pattern that matches:
        # 1. The keyword as-is
        # 2. The keyword + 's' (plural)
        # 3. The keyword + 'es' (plural for words ending in s/x/z/ch/sh)
        # All with word boundaries to prevent substring matches
        # Example: r'\b(hospital|hospitals)\b' matches "hospital" or "hospitals" 
        # but NOT "hospitality"
        pattern = r'\b(' + re.escape(kw) + r'|' + re.escape(kw) + r's|' + re.escape(kw) + r'es)\b'
        if re.search(pattern, lowered):
            matched.append(kw)
    return matched


def is_relevant(item):
    """
    An item is relevant if any configured keyword appears in its title or
    summary as a complete word (not substring), AND it's not a known non-news pattern.
    Returns (bool, matched_keywords_list) so callers can store
    which terms triggered the match -- useful for tuning the list later.
    """
    haystack = f"{item.get('title', '')} {item.get('summary', '')}"
    matches = matched_keywords(haystack)
    
    # Filter out common false positives: job postings, recruitment, tenders, etc.
    # These appear in health-related websites but aren't news
    non_news_patterns = [
        r'\bconsultancy\b',
        r'\bconsultant\b',
        r'\brecruitment\b',
        r'\bjob offer\b',
        r'\bvacancy\b',
        r'\bposition\b',
        r'\btender\b',
        r'\btraining offer\b',
        r'\bcall for applications\b',
        r'\bapplication deadline\b',
    ]
    
    lowered = haystack.lower()
    for pattern in non_news_patterns:
        if re.search(pattern, lowered):
            # Found a non-news pattern, reject even if keywords match
            return (False, [])
    
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
