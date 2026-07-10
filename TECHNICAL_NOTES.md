# Technical Notes / Handoff

## Current status (Phase 1)

Working, tested, end-to-end pipeline for **text-based news only**:
Google News RSS + direct RSS + PubMed -> filter -> dedup -> score -> store
-> export. Radio/TV/YouTube and social media (X) are not yet implemented
-- see "Next collectors to add" below.

All logic has been verified with offline unit tests and an end-to-end
synthetic-data demo (`tests/test_pipeline.py`, `demo_offline_run.py`),
since this environment has no live network access. **Before relying on
this in production, run a real scan against live feeds** (`python scan.py
--mode daily`) and sanity-check the output -- live RSS/PubMed responses
can differ from the synthetic fixtures in edge cases the tests don't cover.

## Known gaps to close before the pilot

1. **`DIRECT_RSS_FEEDS` has only one verified entry** (The New Times).
   This was deliberate -- rather than guess at RSS URLs for every outlet
   in the source inventory and risk pointing at broken/wrong feeds, the
   system leans on Google News RSS for broad coverage in the meantime.
   During the Phase 1 source audit, visit each priority outlet
   (KT Press, IGIHE, Taarifa, Panorama, Kigali Today, Le Canape, etc.),
   check for `/feed`, `/rss`, or a footer link, and add confirmed feeds to
   `config.py`.

2. **PubMed date filtering is approximate.** `esummary` doesn't always
   return a cleanly parseable per-article date, so `published_at` is left
   as `None` for PubMed items and the date range is enforced server-side
   via the `mindate`/`maxdate` params on the `esearch` call instead. This
   is documented behavior (see `scan.within_window`, which keeps
   unknown-date items rather than dropping them) but worth revisiting if
   PubMed's response format changes.

3. **The keyword list (`config.KEYWORDS`) is a starter, not a final
   list.** Expect to miss some relevant stories and catch some
   irrelevant ones until it's tuned against a few real scans. Track this
   during the pilot (Section 18 of the technical design guide --
   "shortlist precision").

4. **Dedup threshold (`TITLE_SIMILARITY_THRESHOLD` in `processing/dedup.py`,
   currently 0.72)** was set based on the test fixtures, not real headline
   data. Watch for two failure modes during the pilot: distinct stories
   incorrectly merged (threshold too low) or true duplicates not merged
   (threshold too high), and adjust.

## Design decisions worth knowing about

- **No `feedparser` or `rapidfuzz` dependency.** Both are common choices
  for this kind of work, but this build uses only `xml.etree.ElementTree`
  and `difflib` from the standard library, plus `requests` (already
  present in most Python environments). One fewer thing to break, install,
  or go unmaintained. If dedup accuracy needs to improve significantly at
  scale, revisit `rapidfuzz` as a fast-follow -- it's still free.
- **`within_window` keeps items with an unknown publish date** rather than
  dropping them, on the theory that a missed story is worse than an extra
  item in the shortlist for the editor to glance at and dismiss.
- **Each collector fails independently** (try/except around every network
  call, logged and skipped). A broken feed should never take down the rest
  of a scan.
- **The `items` table has a `UNIQUE(url)` constraint**, so the same URL is
  never stored twice across multiple scans -- re-running a scan for the
  same period is safe and won't duplicate the archive.

## Next collectors to add (not yet built)

- **Radio & TV via YouTube Data API** -- for RBA, TV1 Rwanda, BTN TV.
  Should follow the same `collect() -> list of item dicts` interface as
  the existing collectors so it drops into `scan.py` with one added line.
- **Social media (X)** -- via Twikit/Twscrape with a dedicated account, per
  Section 6.4 of the technical design guide. This one should be built with
  extra error isolation given its lower reliability, and should not block
  a scan's other collectors if it fails entirely.

## Next steps for the editorial review interface

Right now the "interface" is a CSV file. That's a deliberate, zero-cost
starting point -- an editor opens it in Excel/Sheets, fills in `include`
and `editor_summary` columns. If that proves too clunky in practice, the
natural next step (still free) is a small local web app (e.g., Flask) over
the same SQLite database, so review happens in a browser instead of a
spreadsheet. Nothing in the current schema needs to change for that.
