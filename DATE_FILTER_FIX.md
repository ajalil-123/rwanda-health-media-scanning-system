# Date Filter Fix — scans return only news from the requested date range

## The problem

When you scanned by a specific day or weekly range, older news still showed
up. Items **with** a real publish date (Google News, The New Times, KT
Press, Taarifa — all RSS) were already filtered correctly. The leak came
from items with **no** date.

`within_window` in `scan.py` used to say:

```python
if pub is None:
    return True   # keep every item with no date
```

The web scrapers (IGIHE, Panorama, Kigali Today, The Chronicles) always
returned `published_at = None` — they read a site's **homepage**, which
doesn't say when each headline was published and shows whatever is current
on the day you run the scan, not the day you asked for. So every undated
homepage headline passed the window unconditionally. That was the old news.

## The fix (two parts)

### Part 1 — strict window + date recovery

1. **Strict window (`scan.py`).** An item whose date can't be confirmed
   inside the requested day/week is now **dropped** by default. Dated items
   are unchanged. Optional escape hatch: `KEEP_UNDATED_ITEMS = True` in
   `config.py` reverts to keeping undated items (higher recall, some may be
   out of range).

2. **URL date recovery (`collectors/rss_utils.py` + `collectors/web_scraper.py`).**
   Many permalinks embed the date, e.g. `/2026/07/14/story-slug`. New helper
   `extract_date_from_url()` pulls it out for free (no request), so scraped
   items with dated URLs get filtered by the window like RSS items.

3. **Upstream-filtered marker (`collectors/pubmed.py`).** PubMed has no
   per-item date but already limits results to your window at the API level,
   so its items carry `date_filtered_upstream=True`, which `within_window`
   trusts and keeps.

### Part 2 — article-page date fetching (recovering dates URLs don't carry)

Some sites' article URLs carry no date (e.g. Kigali Today's SPIP-style
URLs). Their pages, however, almost always state a real publish date. So the
web scraper now has a **second** date-recovery step: for headlines that URL
parsing didn't date, it fetches the article page and reads the date from it
(via the existing `extract_date_from_element()` — `<time>` tags, date CSS
classes, Open Graph / schema meta).

Fetching a page per article is exactly what caused the original Render
timeouts, so this step is tightly bounded:

- **Keyword filter first.** A request is spent only on headlines whose title
  matches your health keyword list. There's no point fetching the date of a
  football story you're about to discard — so on a typical day this is a
  handful of fetches, not hundreds.
- **Count cap** — `ARTICLE_DATE_FETCH_MAX` (default 20) fetches per scan.
- **Wall-clock budget** — `ARTICLE_DATE_FETCH_BUDGET_SECONDS` (default 10s)
  total across all article fetches, so a run of slow pages can't accumulate
  past the budget.
- **Short per-request timeout** — `ARTICLE_DATE_FETCH_TIMEOUT_SECONDS`
  (default 5s), so one hung page is bounded too.
- **Off switch** — `ARTICLE_DATE_FETCH_ENABLED = False` disables it entirely.

Worst-case added time ≈ budget + one request timeout ≈ 15s; typical case is
a few seconds because so few headlines match. Items still undated after both
steps fall to the strict window (dropped unless `KEEP_UNDATED_ITEMS`).

## Files changed

| File | Change |
|------|--------|
| `scan.py` | `within_window` is strict; undated items dropped unless `date_filtered_upstream` or `KEEP_UNDATED_ITEMS` |
| `collectors/rss_utils.py` | Added `extract_date_from_url()`; `fetch_url()` gained an optional `timeout`; added a module `logger` (also fixes a latent `NameError` in `extract_date_from_element`) |
| `collectors/web_scraper.py` | URL date recovery + budgeted article-page date fetching (keyword-filtered, count/time/timeout caps) |
| `collectors/pubmed.py` | Items marked `date_filtered_upstream=True` |
| `demo_offline_run.py` | Research fixture marked `date_filtered_upstream=True` so it still flows through |
| `tests/test_date_window.py` | **New** — strict window + URL date extraction |
| `tests/test_article_date_fetch.py` | **New** — article-page fetch ordering, cap, disable switch |

## One manual step

Delete this now-obsolete method from `tests/test_pipeline.py` (it asserts the
OLD behaviour and fails by design). It's in the `TestScanWindow` class:

```python
def test_item_with_unknown_date_is_kept_not_dropped(self):
    start = datetime(2026, 7, 3, tzinfo=timezone.utc)
    end = datetime(2026, 7, 10, 23, 59, 59, tzinfo=timezone.utc)
    item = {"published_at": None}
    self.assertTrue(scan.within_window(item, start, end))
```

Its replacement is `test_undated_item_is_dropped_by_default` in
`tests/test_date_window.py`. Everything else in `test_pipeline.py` still
passes unchanged.

## Optional: expose the toggles in config.py

The fix works without this (code defaults are baked in via `getattr`). To
make the knobs visible and easy to change, add near the "Scan settings"
block in `config.py`:

```python
# Undated items (mostly homepage scrapes) can't be proven in-range.
#   False (default): drop them -> only in-range news shows.
#   True: keep them -> higher recall, some may be out of range.
KEEP_UNDATED_ITEMS = False

# Article-page date fetching for scraped headlines that URL parsing didn't
# date. Conservative defaults for Render free tier (30s worker); raise them
# on a paid plan or when running via cron (no timeout).
ARTICLE_DATE_FETCH_ENABLED = True
ARTICLE_DATE_FETCH_MAX = 20            # max article fetches per scan
ARTICLE_DATE_FETCH_BUDGET_SECONDS = 10 # wall-clock ceiling across those fetches
ARTICLE_DATE_FETCH_TIMEOUT_SECONDS = 5 # per-request timeout (< the feed timeout)
```

## How to verify

```bash
python -m unittest discover tests -v     # after deleting the obsolete method
python demo_offline_run.py               # completes; sanity checks pass
python scan.py --mode daily --date 2026-07-06   # a real past-date scan
```

On a real scan, watch the log for `Article date-fetch: fetched N page(s),
recovered a publish date for M`, and check the Sources Dashboard: a scraped
source should now land items "In Window" instead of showing high "Collected"
but "In Window: 0".

## Trade-offs worth knowing

- A site whose article pages ALSO don't expose a readable date (no `<time>`,
  no date class, no date meta) still can't be dated, and its items are
  dropped under strict mode. `extract_date_from_element()` is best-effort;
  I could not verify it against IGIHE/Panorama/Kigali Today/Chronicles from
  here — confirm with a real scan and watch the log line above.
- The keyword-filter-first design means article dates are fetched only for
  health-matching headlines. That's the point (it keeps you under the Render
  timeout), but on an unusually heavy news day, matches past the cap stay
  undated and get dropped. Raise `ARTICLE_DATE_FETCH_MAX`/budget if you run
  off Render's free tier.

## Secondary note (not changed here)

Day boundaries are computed in **UTC**, but Rwanda is UTC+2. A story
published just after midnight Kigali time lands in the previous UTC calendar
day. If that edge matters, compute the window in `Africa/Kigali` and convert
to UTC in `compute_window` — but that changes the `TestScanWindow`
assertions that currently expect UTC boundaries.
