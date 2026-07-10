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

1. **`DIRECT_RSS_FEEDS` source audit -- in progress.** As of this update,
   **3 outlets are confirmed working**: The New Times, KT Press, and
   Taarifa (all verified by fetching the feed directly and confirming a
   valid `application/rss+xml` response with real content). Two more were
   found but need follow-up before enabling:
   - **Imvaho Nshya** (`imvahonshya.co.rw/feed/`) -- cited by a curated
     RSS directory, but a direct fetch returned a server error during
     verification. Could be transient (worth retrying) or could indicate
     the site blocks automated requests -- needs a re-check.
   - **Rwanda Today** (Nation Media Group) -- feed URL is known, but the
     site's `robots.txt` disallows automated fetching. This is a policy
     question, not just a technical one -- worth a decision on whether to
     respect that before adding it as a collector.

   **IGIHE has no reliable feed.** Its English subdomain exposes a feed,
   but the output is corrupted by PHP warnings printed before the XML
   (will fail to parse -- `rss_utils.parse_feed` handles this gracefully
   by returning zero items, not crashing, but it means IGIHE effectively
   won't be collected via this route). The main Kinyarwanda site
   (igihe.com) runs on SPIP, which usually exposes a feed via
   `?page=backend`, but this wasn't confirmed.

   **Still unchecked**: Panorama, Kigali Today, Umuseke, Le Canapé, La
   Nouvelle Relève, The Chronicles. These remain covered only by the
   Google News RSS broad-discovery layer until individually verified.

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

## Date-window design (updated)

`scan.py --date YYYY-MM-DD` drives strict, calendar-aligned windows:
`--mode daily --date X` scans exactly the calendar day X (00:00:00 to
23:59:59 UTC). `--mode weekly --date X` scans a period ending on X --
either the default 7 calendar days, or, if `--start-date` is also given,
any custom period the user specifies (e.g. 10 days covering a specific
event). This replaced an earlier `--end-date` design where the given date
was treated as the window's *end timestamp* -- which was confusing
(asking for "July 6" actually gave you the day *before* July 6) and not
reproducible (the window depended on what time of day `datetime.now()`
happened to return). The new design is pure calendar-date math: the same
`--mode`/`--date`/`--start-date` combination always computes the identical
window, regardless of when it's actually executed -- verified in
`TestScanWindow.test_repeated_calls_with_same_date_are_identical`.

**Update: scans no longer require the terminal.** `webapp/app.py` now has
a `/new-scan` form -- daily mode shows a single date picker, weekly mode
shows start/end date pickers (start optional, defaults to the standard
7-day period). Submitting runs `scan.run_scan()` synchronously within the
request and redirects straight to the new scan's review page. This is
deliberately simple (no background job queue) -- fine for an internal tool
where the person clicking the button is also the one waiting for it, but
worth revisiting with a background task (e.g. Celery, or even a simple
thread) if scans start taking long enough that the browser request times
out, or if this needs to support multiple concurrent users triggering
scans.

One caveat worth knowing: day boundaries are computed in UTC, not Rwanda's
local time (UTC+2). For a day-level scan this rarely matters, but an item
published right around 22:00-00:00 Rwanda time could land in the
"neighboring" UTC calendar day rather than the one a Rwanda-based user
would intuitively expect. Worth revisiting if this proves confusing in
practice -- the fix would be computing day boundaries in Africa/Kigali
time and converting to UTC only for the actual comparison.

## Diagnostics for "no health news is showing up"

Added per-collector and per-stage visibility to `scan.py` specifically
because an empty shortlist was previously ambiguous -- it could mean the
network was blocked, the date window excluded everything collected, or
the keyword list didn't match anything that day, and there was no way to
tell which from the output. Now:

- Each collector's raw item count is logged individually
  (`google_news`, `direct_rss`, `pubmed`), and a crashing collector
  (not just one returning `[]`) is caught so it can't take down the
  whole scan -- covered by `test_a_crashing_collector_does_not_crash_the_whole_scan`.
- A sample of up to 5 raw collected titles is logged, so you can eyeball
  whether collection is happening at all before worrying about filtering.
- Explicit WARNING messages fire for the three ambiguous cases: zero raw
  items (→ likely network/access issue), items collected but all outside
  the window (→ likely a Google-News-freshness issue, try widening the
  range), and items in-window but none keyword-matched (→ quiet day or
  keyword list gap).
- A per-section breakdown (`local_online`/`international`/`research`
  counts) is logged, so a gap in one section specifically (e.g. local
  media coming back empty while research doesn't) is visible immediately
  rather than requiring a database query to notice.
- All of this is returned from `run_scan()` in a `diagnostics` dict, and
  the web app's `/run-scan` route uses it to show a specific, useful flash
  message instead of just an item count.

This was prompted by a real report of "local media isn't generating any
health news" -- worth checking against the new diagnostic output first
before assuming it's a keyword or source-list problem, since it could
just as easily be a network-access issue in a particular deployment
environment.

## Web scraper collector for sites without RSS (IGIHE, Panorama, Kigali Today, The Chronicles)

Added `collectors/web_scraper.py` as a fourth collector, specifically to
close the gap flagged earlier: several priority local outlets have no
reliable RSS feed. Honest constraint acknowledged upfront rather than
worked around: **I could not verify real CSS selectors for these sites'
actual HTML structure from this environment** -- the tools available for
fetching pages here return cleaned/extracted content for reading, not raw
HTML suitable for deriving exact selectors, and I didn't want to guess at
selectors and silently ship something that returns nothing (or worse,
returns confidently-wrong noise) against the live sites.

Instead, this collector:
- Ships with a **generic heuristic** (tries common headline-selector
  patterns first, falls back to filtering every link on the page by
  length/same-site checks) that will produce *something* against most
  WordPress-style or conventionally-structured sites without any
  per-site configuration.
- Supports a `link_selector` field per site in `config.SCRAPE_SITES` that,
  once set, bypasses the generic heuristic entirely for that site.
- Logs clearly, every time it falls back to the generic heuristic, that
  it's doing so -- so this isn't silently assumed to be production-ready.
  Real verification requires someone with a browser inspecting the live
  page and filling in the selector (steps are in `README.md`).

Tested thoroughly against synthetic HTML fixtures (WordPress-style
`article > h2.entry-title > a` pattern, and a more generic `.story > a`
pattern) covering: configured-selector extraction, the generic fallback,
nav/footer link exclusion, off-site link exclusion (a real bug was caught
here -- initial version used substring domain matching, which let
`external-ads.example.com` through as if it were `example.com`; fixed to
an exact host match), relative-URL resolution, same-page deduplication,
and graceful handling of network failures and malformed HTML. 78 tests
total now.

**Real-world next step, not yet done**: run a scan against live internet
access, open the generated shortlist, and check whether IGIHE/Panorama/
Kigali Today/The Chronicles entries look like real headlines or noise. If
noisy, follow the README's selector-finding steps for that specific site.

## Critical fix: shortlist showing 0 items despite diagnostics saying otherwise

**Symptom reported**: the scan's flash message said "1 items in the
shortlist," but the actual review page for that scan showed 0 items.

**Root cause**: `items` had a global `UNIQUE(url)` constraint, meant to
stop a *single* scan from storing the same article twice. But it applied
across *all* scans, not just one -- so if an article's URL had ever been
stored before (an earlier scan, a re-run, or the same story still being
returned by Google News the next day), `insert_item()` silently skipped
it on every later scan. The item was correctly collected, filtered, and
counted in that scan's diagnostics -- it just never actually got saved
under that scan's `scan_id`, because the URL "belonged" to whichever scan
first saw it.

**Fix**: changed the constraint to `UNIQUE(scan_id, url)` -- still
prevents true duplicates within one scan (e.g. Google News and a direct
RSS feed both surfacing the identical URL), but correctly allows the same
article to appear in multiple different scans, each getting its own row.

**Migration**: SQLite can't alter a constraint in place, so
`db.init_db()` now detects the old schema (by inspecting
`sqlite_master`'s stored CREATE TABLE SQL) and automatically rebuilds the
`items` table with the fixed constraint, preserving all existing rows.
This runs automatically the next time the app starts -- **no manual
database deletion needed**, and it's safe to run repeatedly (a no-op once
already migrated). Covered by
`test_migration_fixes_a_pre_existing_old_schema_database`, which
recreates the exact old schema, migrates it, and confirms both the data
survives and the bug is actually fixed afterward.

## Next steps for the editorial review interface

**Update: this is now built.** `webapp/app.py` is a small local Flask app
over the same SQLite database -- run `python webapp/app.py` and open
`http://127.0.0.1:5000`. It lists all scans, shows each one's shortlist
grouped into the report's three sections, and lets an editor check
"include," write the summary, and save -- all persisted back to
`media_monitor.db` via two new columns (`included`, `editor_summary`) added
through an automatic migration in `db.init_db()`, so existing databases
don't need to be deleted/recreated to pick this up.

The CSV/Markdown export in `export.py` still works and is unaffected --
useful as a lightweight alternative if a particular reviewer would rather
work in a spreadsheet than a browser.

Still manual, by design: report drafting into the actual Word template.

**Update: this is now built too.** `report_generator.py` reads
`included`/`editor_summary` back out of SQLite (via `db.get_included_items`)
and uses `python-docx` to produce a `.docx` matching RBC's existing
template -- Highlights, I. Local Media > A. Online, II. International
Media, III. Research Findings, with real clickable hyperlinks (built by
hand via OOXML, since python-docx has no native hyperlink support). Wired
into the web app as a "Generate Word Report" button on each scan's review
page (`/scan/<id>/generate-report`), and callable directly from Python or
another script.

**I.B Radio & TV and IV. Social Media Trends are placeholder sections** in
the generated document -- correct headings, with a note that they need
manual completion, since those collectors don't exist yet (see "Next
collectors to add" above). Once they're built, `report_generator.py`'s
`by_category` grouping just needs two more keys (`radio_tv`, `social_media`)
added -- the rest of the generation logic doesn't change.

One implementation note: Flask's `send_file` resolves relative paths
against the app's `root_path` (the `webapp/` folder), not the process's
working directory -- caught this via testing the actual route, not just
calling `generate_report()` directly. Fixed by having the web app pass an
absolute path, and by having `report_generator.py`'s default output
location resolve relative to its own file location rather than `cwd`, so
behavior is consistent regardless of where anything is launched from.
