# rwanda-health-media-scanning-system -- Phase 1 (Text-Based News)

A no-cost, semi-automated system that scans text-based health news relating
to Rwanda and produces a reviewable shortlist for RBC's media review team.
Built to run daily and weekly scans, each strictly scoped to that day's or
that week's content only.

This is **Phase 1**: local online news, international media, and research
journals. Radio/TV/YouTube and social media (X) collectors are intentionally
out of scope for this phase and can be added as new modules later without
changing the existing structure (see `TECHNICAL_NOTES.md`).

## What it does

1. Collects raw items from three free sources:
   - **Google News RSS** -- broad discovery across the wider media landscape
   - **Direct RSS feeds** -- known priority outlets (starts with The New Times;
     add more as they're verified)
   - **PubMed E-utilities** -- research & journal articles mentioning Rwanda
2. Restricts results to a strict date window: the current day for a daily
   scan, the trailing 7 days for a weekly scan -- not an ever-growing pile.
3. Filters for health relevance using a maintained multilingual (English /
   Kinyarwanda / French) keyword list -- no paid AI involved.
4. Deduplicates near-identical coverage of the same story across outlets,
   robust to headlines being reworded/reordered between publishers.
5. Scores and ranks items for a proposed Highlights list (transparent
   heuristic: outlet count + keyword signal + recency).
6. Stores everything in a local SQLite database (`media_monitor.db`, a
   single file -- no server needed) and exports a **CSV** and **Markdown**
   shortlist for the editorial team to review, select from, and write
   summaries into, the same way they do today.

## What it deliberately does NOT do

It does not write the report for you. Selecting which items matter and
writing the summary text in the report's existing style stays a manual,
editorial step -- this system's job is to replace the time spent visiting
dozens of sites and accounts, not to replace editorial judgment.

## Generating the final Word report

Once you've reviewed a scan in the web app (checked "Include," written
summaries, clicked **Save review**), click **Generate Word Report** on the
same page. This produces a `.docx` matching RBC's existing template
structure -- Highlights, I. Local Media (A. Online), II. International
Media, III. Research Findings -- populated only with the items you marked
included, using the summaries you wrote.

Two sections are included as placeholders, since they aren't automated
yet: **I.B Radio & TV** and **IV. Social Media Trends**. The generated
document has the correct headings for both, with a note explaining they
need to be filled in manually until those collectors are built.

You can also generate a report from the command line:
```python
import report_generator
report_generator.generate_report(scan_id=1)
```

## Viewing results in a web app (instead of CSV)

A small local web app is included for reviewing scan results in a browser
-- runs entirely on your own machine, no hosting cost.

```bash
pip install -r requirements.txt   # now includes flask
python webapp/app.py
```

Then open **http://127.0.0.1:5000** in your browser. You'll see:

- A landing page listing every scan you've run (daily and weekly), with
  raw/relevant/unique counts
- Click into a scan to see its shortlist grouped into the report's three
  sections (Local Online, International, Research), each item showing its
  highlight score, matched keywords, and which other outlets covered the
  same story
- Check "Include in report" and type the summary directly in the browser,
  then click **Save review** -- this writes back to the same
  `media_monitor.db` SQLite file, so nothing about the scanning pipeline
  changes

Stop the app with `Ctrl+C` in the terminal when you're done. It only runs
while you have that terminal open -- it's not a background service.

## Setup

```bash
cd rwanda-health-media-scanning-system
pip install -r requirements.txt   # requests + flask
```

No API keys, no paid accounts, no cloud services required for this phase.

## Sources Coverage — knowing which websites were checked

On every scan's review page, below the shortlist, there's a **Sources Coverage** table showing which websites were actually queried and how many relevant health items came from each. This includes sources with zero items so you can see "we checked Google News, The New Times, KT Press, Taarifa, IGIHE, Panorama, Kigali Today, The Chronicles, web scrapers, and PubMed — here's what each found."

The table tracks four stages for each source:
- **Collected** — items the source returned (before any filtering)
- **In Window** — items that fell within your requested date range
- **Relevant** — items matching the health keyword list
- **Unique (Shortlist)** — items remaining after deduplication

So if Google News shows "Collected: 145, In Window: 12, Relevant: 0, Unique: 0" — you know it worked, returned content for the right date, but nothing matched health keywords that day. That's very different from "Collected: 0" which means a network/access issue.

## Scraping sites with no working RSS feed

For local outlets that don't have a reliable feed (IGIHE, Panorama, Kigali
Today, The Chronicles, per the source audit in `TECHNICAL_NOTES.md`), a
fourth collector (`collectors/web_scraper.py`) scrapes their homepage/news
listing page directly, using `requests` + BeautifulSoup (both free).

**It ships with a generic heuristic that works out of the box but is
noisy** -- it looks for common headline patterns (`article h2 a`,
`.entry-title a`, etc.) and falls back to filtering every link on the
page by length and same-site checks if none of those patterns match nothing.
This is a starting point, not a finished configuration.

**To get a precise, low-noise scrape for a specific site:**

1. Open the site in a browser (e.g. `en.igihe.com`).
2. Right-click a headline on the homepage → **Inspect**.
3. Note the CSS pattern the site uses -- e.g. if the headline is inside
   `<h2 class="entry-title"><a href="...">`, the selector is
   `h2.entry-title a`.
4. Open `config.py`, find that site's entry in `SCRAPE_SITES`, and set
   `"link_selector": "h2.entry-title a"`.
5. Re-run a scan and check the terminal log for `Web scrape <site>
   returned N candidate items` -- open `output/*_shortlist_*.csv` and spot
   check a few of that site's entries to confirm they're real headlines,
   not nav/ad junk.

Until a site has a `link_selector` set, every scan logs a reminder that
it's using the generic fallback for that site.

**Limitations worth knowing:**
- No publish date is available from a listing page (only from visiting
  each article individually, which this collector deliberately doesn't
  do, to keep the number of requests low). Items get `published_at=None`,
  which the pipeline treats as "keep it" rather than dropping it.
- This collector does not check `robots.txt` automatically -- check each
  site's policy yourself before enabling it, the way the Rwanda Today RSS
  feed was deliberately left disabled over exactly this concern.
- Sites that render their homepage via JavaScript (rather than plain
  HTML) won't work with this approach -- `requests` only gets the initial
  HTML, not what JavaScript adds afterward. That would need a headless
  browser tool (e.g. Playwright), which is a heavier addition than this
  collector currently makes.

## Deleting scans

Scans accumulate quickly, especially while testing. From the landing page:

- **Delete** next to any scan row removes that scan and all of its items
  (with a confirmation prompt).
- **Delete all scans** clears everything at once (with a stronger
  confirmation prompt, since it's irreversible).

Both act directly on `media_monitor.db` -- there's no undo, so use them
deliberately. Generated report/shortlist files in `output/` are not
deleted automatically; clean those up separately if needed.

## Data Sources & Collection

The system now collects health news from **8 different sources** across news, research, government, and social media:

### 1. **Google News RSS** (Broad Discovery)
- 5 multilingual queries: "health Rwanda", "Rwanda hospital", "ubuzima Rwanda", etc.
- Catches major international outlets automatically
- ~100-150 items per scan

### 2. **Direct RSS Feeds** (Verified Local Outlets)
- The New Times
- KT Press
- Taarifa
- ~20-50 items total

### 3. **Web Scrapers** (Outlets Without RSS)
- Local: IGIHE, Panorama, Kigali Today, The Chronicles
- International: Reuters, BBC, AFP, Al Jazeera, France 24, DW, Africanews
- Official: Rwanda Ministry of Health, RBC, WHO Rwanda
- ~30-50 items total

### 4. **PubMed** (Research & Journals)
- Academic papers, journal articles
- ~0-10 items per scan

### 5. **Academic Sources** (NEW)
- Google Scholar (Rwanda health)
- ResearchGate (Rwanda health research)
- SSRN (Rwanda health policy/economics)
- arXiv (Rwanda)
- ~0-20 items per scan

### 6. **Social Media** (NEW - Twitter/X)
- Configured accounts: @RwandaHealth, @RBCRwanda, @WHORwanda, etc.
- Hashtags: #RBAAmakuru, #RwandaHealth, #ubuzima, etc.
- Requires dedicated RBC X account (see "Twitter Configuration" below)

### 7. **Official Sources** (NEW)
- Rwanda Ministry of Health announcements
- Rwanda Biomedical Centre news
- WHO Rwanda country page
- ~5-15 items per scan

### 8. **International News** (NEW)
- Reuters Africa
- BBC News Africa
- AFP
- Al Jazeera
- France 24
- DW News
- Africanews
- Filtered to show only Rwanda-related stories
- ~5-20 items per scan

---

## Configuration

All sources are configured in `config.py`. To add, modify, or disable sources:

### Add an International Outlet
```python
INTERNATIONAL_SOURCES = [
    {
        "name": "Your Outlet Name",
        "url": "https://example.com/news/",
        "language": "en",
        "category": "international",
        "link_selector": "h2.headline a",  # CSS selector for article links
    },
]
```

### Add an Official Source
```python
OFFICIAL_SOURCES = [
    {
        "name": "Your Organization",
        "url": "https://example.org/announcements/",
        "language": "en",
        "category": "local_online",
        "link_selector": None,  # Will use generic scraper if None
    },
]
```

### Add a Research Source
```python
RESEARCH_SOURCES = [
    {
        "name": "My Research Database",
        "url": "https://example.org/search",
        "query": "Rwanda health",
        "source": "custom_scraper",  # identify the type
    },
]
```

### Twitter Configuration (Optional)

To enable Twitter/X monitoring:

1. Create a dedicated RBC account (not your personal account) on X
2. Add to `config.py`:
```python
TWITTER_EMAIL = "rbc.health@example.com"
TWITTER_PASSWORD = "your_password_here"
# Optional: TOTP secret for 2FA
TWITTER_TOTP_SECRET = "your_totp_secret"

SOCIAL_MEDIA_ACCOUNTS = {
    "twitter": [
        "@RwandaHealth",
        "@RBCRwanda",
        "@WHORwanda",
    ],
    "hashtags": [
        "#RBAAmakuru",
        "#RwandaHealth",
    ],
}
```

3. First run will require interactive verification; subsequent runs use cached auth
4. Install Twikit: `pip install twikit`

---

## Finding CSS Selectors

To configure web scrapers for a new site with a precise CSS selector:

1. Open the website in your browser
2. Right-click on a headline → "Inspect Element"
3. Look for the pattern, e.g.:
   - `<h2 class="entry-title"><a href="...">Headline</a></h2>` → selector is `h2.entry-title a`
   - `<div class="news-item"><a href="...">Headline</a></div>` → selector is `div.news-item a`
4. Add to the appropriate config section (INTERNATIONAL_SOURCES, OFFICIAL_SOURCES, SCRAPE_SITES)
5. Test by running a scan and checking the terminal output

## Troubleshooting

### Some sources return 0 items

**Possible reasons:**
1. Website is blocking automated requests (check terminal for specific error)
2. No health-related articles on that day
3. CSS selector is incorrect (change to None to use generic fallback)
4. Site structure changed (update the selector)

**Solution:** Check the per-source breakdown in the Sources Dashboard to see which stage items are getting filtered out.

### Twitter collector isn't working

**Possible reasons:**
1. Twikit not installed: `pip install twikit`
2. Credentials missing from config.py
3. X account is rate-limited or blocked

**Solution:** Check terminal logs during scan for specific Twikit errors

### Scraper is too noisy

**Problem:** Getting lots of non-health articles
**Solution:** Make sure the keyword list in `config.KEYWORDS` is comprehensive, or adjust CSS selectors to be more specific

## Scraping Etiquette

When adding new sources:
- **Respect robots.txt**: Check the site's `/robots.txt` before enabling
- **Use descriptive User-Agent**: System sends "Rwanda Health Media Monitoring System"
- **Don't parallelize**: Scraping is sequential, not parallel
- **Monitor for blocks**: If a source blocks requests, disable it and respect their policy

## Troubleshooting: "nothing is showing up"

An empty shortlist can mean several different things -- as of this update,
the scan tells you which one via clear WARNING messages in the terminal
(and a matching message in the web app):

- **"Zero raw items from every collector"** -- a network/access problem
  (blocked outbound requests, firewall, proxy), not a lack of news. Check
  the collector-level WARNING lines just above it for the specific error
  from each source.
- **"All N collected items fell OUTSIDE the requested window"** -- the
  collectors are working, but returned older content than the date range
  you asked for. Google News RSS in particular can skew several days old.
  Try `--mode weekly` or a wider date range to confirm collection itself
  is working.
- **"N items were in the window but NONE matched the health keyword
  list"** -- collection and windowing are both fine; either it was a quiet
  day for health news, or `config.KEYWORDS` needs broadening. The log
  prints a sample of the actual titles collected so you can check.

Every scan also logs a **per-collector breakdown** (`google_news`,
`direct_rss`, `pubmed` item counts) and a **per-section breakdown**
(`local_online`, `international`, `research` counts) so you can see
exactly where coverage is thin.

## Running a scan -- from the web app (recommended)

Open the web app (see below) and click **+ Run a new scan** on the landing
page:

- **Daily**: pick one date. Scans exactly that calendar day.
- **Weekly**: pick a period end date, and optionally a period start date.
  Leave the start date blank for the default 7-day period ending on your
  chosen date, or set it explicitly to scan any custom period -- e.g. 10
  days covering a specific outbreak response.

The scan runs immediately when you submit, and you're taken straight to
its review page once it finishes.

## Running a scan -- from the command line

```bash
# Today's daily scan
python scan.py --mode daily

# This week's weekly scan (7 days ending today)
python scan.py --mode weekly

# A specific past day -- scans exactly that calendar day, nothing else
python scan.py --mode daily --date 2026-07-06

# A specific past week -- the 7 days ending on (and including) that date
python scan.py --mode weekly --date 2026-07-06

# A custom period -- any start and end date, not just 7 days
python scan.py --mode weekly --start-date 2026-06-20 --date 2026-06-30
```

`--date` gives you full control over which day/week is scanned. Running the
same `--mode`/`--date` combination always computes the exact same window,
no matter what time you actually run it -- `--mode daily --date 2026-07-06`
always means the full calendar day of July 6th (00:00:00 to 23:59:59 UTC),
whether you run it that same day or catch up on it a week later. Without
`--date`, it defaults to today.

Each run creates/updates `media_monitor.db` and writes two files to `output/`:

- `output/{mode}_shortlist_{date}.csv` -- open in Excel/Google Sheets;
  editor marks `include` (Y/N) and fills in `editor_summary` per item
- `output/{mode}_shortlist_{date}.md` -- quick-read version, grouped by
  report section

## Scheduling (free)

Run on any existing computer/server RBC already has, via `cron`:

```cron
# Daily scan at 7am
0 7 * * * cd /path/to/rwanda-health-media-scanning-system && python3 scan.py --mode daily

# Weekly scan Monday 6am, covering the past 7 days
0 6 * * 1 cd /path/to/rwanda-health-media-scanning-system && python3 scan.py --mode weekly
```

Or use a scheduled GitHub Actions workflow if the code lives in a repo --
free tier is generous at this scale.

## Configuration

Everything you're likely to need to change lives in `config.py`:

- `GOOGLE_NEWS_QUERIES` -- discovery queries (add more topics/languages here)
- `DIRECT_RSS_FEEDS` -- priority outlets with confirmed RSS feeds: **The New
  Times, KT Press, and Taarifa** are verified working as of this audit.
  See `config.py` for candidates found but not yet confirmed (Imvaho
  Nshya, Rwanda Today), and outlets still needing a feed check (Panorama,
  Kigali Today, Umuseke, Le Canapé, IGIHE -- see notes in `config.py` for
  why each of these needs a closer look before adding).
- `PUBMED_QUERY` -- the search term(s) used against PubMed
- `KEYWORDS` -- the multilingual relevance keyword list. Treat this as a
  living document: whenever a relevant story is missed, add the term that
  should have caught it.

## Testing

No live network access is required to verify the system works:

```bash
# Unit tests (feed parsing, filtering, dedup, scoring, windowing, storage)
python -m unittest discover tests -v

# Full pipeline demo using synthetic data, with sanity-check assertions
python demo_offline_run.py
```

## Project layout

```
config.py                  -- sources, keywords, scan settings (edit this most)
db.py                       -- SQLite storage
scan.py                      -- main entrypoint (daily/weekly CLI)
export.py                     -- CSV/Markdown shortlist export
report_generator.py             -- generates the final .docx report matching RBC's template
collectors/
  rss_utils.py                -- shared RSS/Atom parsing (stdlib XML, no feedparser)
  google_news.py                -- Google News RSS collector
  direct_rss.py                  -- direct outlet RSS collector
  pubmed.py                        -- PubMed E-utilities collector
processing/
  filter_relevance.py               -- keyword-based relevance filter
  dedup.py                            -- fuzzy duplicate detection
  highlight_score.py                    -- highlight ranking heuristic
tests/
  test_pipeline.py                        -- offline unit tests (25 tests)
demo_offline_run.py                          -- offline end-to-end demo
webapp/
  app.py                                        -- local Flask review app
  templates/                                      -- index.html, scan.html, base.html
  static/style.css                                  -- app styling
```
