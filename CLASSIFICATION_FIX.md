# Fix: KT Press (and other spaced/accented outlets) mislabelled International

## Symptom

A KT Press article ("Rwanda Gov Bans Dozens of Alcohol Drinks...") appeared
under **II. International Media** instead of **I. Local Media**, even though
KT Press is a Rwandan outlet.

## Cause

The item came from the **Google News** collector — the only collector that
guesses a report section from the outlet name. Every other collector takes
its category straight from `config.py`. The guess in
`collectors/google_news._classify_category` compared raw lowercased
substrings:

```python
_LOCAL_OUTLET_HINTS = [..., "ktpress", ...]   # no space
if any(hint in source_name.lower() for hint in _LOCAL_OUTLET_HINTS):
    return "local_online"
return "international"
```

Google News reports the outlet as **"KT Press"** (with a space), so the
lowercased name is `"kt press"`. The hint `"ktpress"` is not a substring of
`"kt press"`, so nothing matched and it fell through to `international`. The
same problem hit any outlet whose spacing/punctuation/accents didn't exactly
match a hint (e.g. `"Le Canapé"` vs `"le canape"`).

## Fix

Normalise both sides before matching: lowercase, strip accents, remove all
non-alphanumeric characters. `"KT Press"`, `"KT PRESS"`, and `"ktpress"` all
collapse to `ktpress` and match; `"Le Canapé"` → `lecanape`. Added
`_normalize()` to `collectors/google_news.py` and routed
`_classify_category()` through it. Anything not recognised as a known local
outlet is still treated as International (unchanged default).

## Scope — only Google News was affected

- **Google News** — fixed.
- **Direct RSS** (New Times, KT Press, Taarifa) — category from
  `config.DIRECT_RSS_FEEDS`, already correct.
- **Web scraper** (IGIHE, Panorama, Kigali Today, Chronicles) — category from
  `config.SCRAPE_SITES`, already correct.
- **PubMed** — hardcoded `research`.
- International / official / academic collectors — disabled. Twitter —
  `social_media` (not a report section).

## Files changed

| File | Change |
|------|--------|
| `collectors/google_news.py` | Added `_normalize()`; `_classify_category()` matches on the normalised name |
| `tests/test_source_classification.py` | **New** — spaced/all-caps/accented locals classify local; BBC/Reuters/Al Jazeera stay international |

This change is independent of the date-filter fix and can be committed on its
own.

## Important: existing scans keep their old categories

`source_category` is decided when an item is collected and stored, so already-
scanned KT Press items stay labelled International in the database. The fix
only affects **new** scans. To correct an existing scan, re-run it (or delete
it and scan that date again).

## Verify

```bash
python -m unittest discover tests -v      # includes the new classification tests
python scan.py --mode daily --date 2026-08-02   # re-scan; KT Press now under Local
```

## Extending

If a NEW Rwandan outlet shows up under International, add its name (readable
form is fine — normalisation handles spacing/accents) to `_LOCAL_OUTLET_HINTS`
in `collectors/google_news.py`.
