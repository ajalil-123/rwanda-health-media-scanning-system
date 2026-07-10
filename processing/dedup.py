"""
Deduplication of near-identical coverage across outlets (Section 7.2 of the
technical design guide).

Uses Python's built-in difflib rather than a third-party fuzzy-matching
library, keeping the dependency list at just `requests`. difflib's
SequenceMatcher is slower than rapidfuzz on large datasets, but at the
scale of a daily/weekly news scan (dozens to low hundreds of items) it is
more than fast enough.

Titles for the same story are often worded differently across outlets
("Rwanda rolls out new malaria protocol" vs "New malaria protocol rolled
out in Rwanda") -- a plain character-sequence comparison penalizes this
word reordering heavily. To handle it, similarity is computed on a
*token-sorted* form of each title (words lowercased, sorted alphabetically,
rejoined) before comparing -- the same trick used by rapidfuzz's
token_sort_ratio -- so reordered-but-equivalent headlines still match.
"""

import re
from difflib import SequenceMatcher

TITLE_SIMILARITY_THRESHOLD = 0.72  # tuned for token-sorted comparison; adjust during the pilot

_WORD_RE = re.compile(r"[a-z0-9']+")


def _normalize(title):
    return " ".join(title.lower().split())


def _token_sorted(title):
    """Lowercase, strip punctuation, sort words alphabetically. This makes
    'malaria treatment protocol rolled out' and 'protocol rolled out for
    malaria treatment' compare as near-identical instead of dissimilar."""
    words = _WORD_RE.findall(title.lower())
    return " ".join(sorted(words))


def title_similarity(a, b):
    """Blend of direct similarity and token-sorted similarity, taking the
    higher of the two -- catches both near-identical strings and
    reordered/reworded headlines about the same story."""
    direct = SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()
    token_sorted = SequenceMatcher(None, _token_sorted(a), _token_sorted(b)).ratio()
    return max(direct, token_sorted)


def deduplicate(items):
    """
    Given a list of relevance-filtered items (each a dict with a 'title'
    key), return (unique_items, duplicate_groups) where:
      - unique_items: one representative item per story, with a
        'covered_by' list of the other source names reporting the same story
      - duplicate_groups: list of lists of the *duplicate* items that were
        folded into a representative (kept for audit/traceability, not shown
        in the shortlist)

    The first item encountered for a story becomes the representative;
    later near-duplicates are folded into it.
    """
    unique_items = []
    duplicate_groups = []

    for item in items:
        match_found = False
        for rep in unique_items:
            if title_similarity(item["title"], rep["title"]) >= TITLE_SIMILARITY_THRESHOLD:
                rep.setdefault("covered_by", [rep["source_name"]])
                if item["source_name"] not in rep["covered_by"]:
                    rep["covered_by"].append(item["source_name"])
                duplicate_groups.append(item)
                match_found = True
                break
        if not match_found:
            unique_items.append(dict(item))

    return unique_items, duplicate_groups
