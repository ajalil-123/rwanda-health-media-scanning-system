# Data Sources Guide

## Overview

This system now collects health news from **8 different sources**. Here's a breakdown of what was added and how to configure each.

---

## 1. International News Sources (NEW)

**Collectors file:** `collectors/international_news.py`

**Configured outlets:**
- Reuters (Africa section)
- BBC News Africa
- AFP News
- Al Jazeera
- France 24
- DW News
- Africanews

**How it works:**
- Scrapes the Africa/international section of each outlet
- Filters results to show only Rwanda-related stories
- Looks for Rwanda mentions in headlines

**Configuration in `config.py`:**
```python
INTERNATIONAL_SOURCES = [
    {
        "name": "Reuters",
        "url": "https://www.reuters.com/world/africa/",
        "language": "en",
        "category": "international",
        "link_selector": "h3 a, .heading-article a",
    },
    # ... more outlets
]
```

**To find the right `link_selector`:**
1. Visit the outlet's news page
2. Right-click a headline → Inspect Element
3. Note the HTML pattern, e.g., `<h3><a href="...">Headline</a></h3>`
4. The selector is: `h3 a`

**Expected output:** 5-20 items per scan

---

## 2. Official Government & Health Organization Sources (NEW)

**Collectors file:** `collectors/official_sources.py`

**Configured sources:**
- Rwanda Ministry of Health (moh.gov.rw)
- Rwanda Biomedical Centre (rbc.gov.rw)
- WHO Rwanda

**Why important:**
- Direct from authoritative sources
- No media gatekeeping — get announcements first
- Official policy changes, emergency alerts

**Configuration in `config.py`:**
```python
OFFICIAL_SOURCES = [
    {
        "name": "Rwanda Ministry of Health",
        "url": "https://www.moh.gov.rw/",
        "language": "en",
        "category": "local_online",
        "link_selector": None,  # Use generic scraper initially
    },
]
```

**To configure precisely:**
1. Visit the organization's website
2. Find the "News" or "Announcements" section
3. Right-click a news headline → Inspect
4. Note the CSS pattern
5. Set `link_selector` to that pattern

**Expected output:** 5-15 items per scan

---

## 3. Academic & Research Sources (NEW)

**Collectors file:** `collectors/academic_sources.py`

**Configured sources:**
- **Google Scholar** - Academic search engine (limited due to blocking)
- **ResearchGate** - Research paper sharing platform
- **SSRN** - Social Science Research Network (economics, policy papers)
- **arXiv** - Open preprints (uses official API, not scraped)

**Why important:**
- Catches research papers on Rwanda health topics
- Policy briefs and working papers
- Preprints not yet published in journals

**Configuration in `config.py`:**
```python
RESEARCH_SOURCES = [
    {
        "name": "Google Scholar Rwanda",
        "url": "https://scholar.google.com/scholar",
        "query": "Rwanda health",
        "source": "google_scholar",
    },
    {
        "name": "arXiv Rwanda",
        "url": "https://arxiv.org/",
        "query": "Rwanda health",
        "source": "arxiv",  # Uses API, not scraper
    },
]
```

**Note:** Google Scholar blocks heavy scraping; results may be limited or empty.

**Expected output:** 0-20 items per scan

---

## 4. Social Media - Twitter/X (NEW, Optional)

**Collectors file:** `collectors/twitter.py`

**What it monitors:**
- Configured Twitter accounts: @RwandaHealth, @RBCRwanda, @WHORwanda, etc.
- Health-related hashtags: #RBAAmakuru, #RwandaHealth, #ubuzima, etc.

**Why important:**
- Real-time alerts and breaking news
- Informal announcements before official news releases
- Community discussions on health topics

**Prerequisites:**
1. Create a dedicated X account for RBC (not personal)
2. Install Twikit: `pip install twikit`

**Configuration in `config.py`:**
```python
TWITTER_EMAIL = "rbc.health@example.com"
TWITTER_PASSWORD = "secure_password"
# Optional, for 2FA:
TWITTER_TOTP_SECRET = "your_totp_secret"

SOCIAL_MEDIA_ACCOUNTS = {
    "twitter": [
        "@RwandaHealth",
        "@RBCRwanda",
        "@WHORwanda",
        "@RwandaHRH",
        "@MinofHealthRwanda",
    ],
    "hashtags": [
        "#RBAAmakuru",
        "#RwandaHealth",
        "#ubuzima",
        "#sante_rwanda",
    ],
}
```

**First run:** Will prompt for email/password verification (interactive). Subsequent runs use cached credentials.

**Expected output:** 5-30 tweets per scan

**Important notes:**
- Requires dedicated account (not personal)
- X may rate-limit or block the account if too aggressive
- Twikit is a browser-automation library; use responsibly
- Check X's terms of service before enabling

---

## Data Collection Pipeline (Updated)

```
┌─────────────────────────────────────────────┐
│ STAGE 1: Collection (8 sources)             │
├─────────────────────────────────────────────┤
│ • Google News (broad discovery)             │
│ • Direct RSS (The New Times, KT Press, etc) │
│ • Web Scrapers (IGIHE, Panorama, etc)       │
│ • International News (Reuters, BBC, etc) NEW│
│ • Official Sources (MOH, RBC, WHO) NEW      │
│ • Academic Sources (Scholar, ResearchGate)  │
│ • PubMed (journals)                         │
│ • Twitter/X (hashtags, accounts) NEW        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ STAGE 2: Date Window Filtering              │
│ (Keep only items from requested date range) │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ STAGE 3: Relevance Filter                   │
│ (Match health keywords)                     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ STAGE 4: Deduplication                      │
│ (Merge same story from multiple outlets)    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ STAGE 5: Scoring & Ranking                  │
│ (Highlight by importance)                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ STAGE 6: Storage & Dashboard                │
│ (SQLite + Sources Dashboard)                │
└─────────────────────────────────────────────┘
```

---

## Total Data Collection Capacity

**Per scan (typical daily):**
- Google News: ~100-150 items
- Direct RSS: ~20-50 items
- Web Scrapers: ~30-50 items
- International News: ~5-20 items
- Official Sources: ~5-15 items
- Academic Sources: ~0-20 items
- Twitter: ~5-30 tweets
- PubMed: ~0-10 items

**Total collected:** ~170-340 raw items
**After filtering:** ~1-10 unique health-related stories

---

## Troubleshooting

### "I'm getting 0 items from a source"

**Check these in order:**

1. **Terminal logs during scan:**
   ```
   python webapp/app.py
   # Look for source-specific WARNING messages
   ```

2. **Per-source breakdown** (Sources Dashboard):
   - If `Collected: 0`, the source isn't returning anything
   - If `Collected: >0` but `Relevant: 0`, nothing matched health keywords

3. **For web scrapers:**
   - Check if the website's structure changed (CSS selectors may be outdated)
   - Try setting `link_selector: None` to use generic fallback
   - Visit the site in your browser — is content actually there?

4. **For Twitter:**
   - Is Twikit installed? `pip install twikit`
   - Are credentials in `config.py`?
   - Is the RBC account rate-limited? (X enforces strict limits)
   - Check for TOTP/2FA errors in logs

5. **For international/official sources:**
   - Is the site accessible? Try visiting it manually
   - Has the site blocked your IP? (some sites block automated requests)
   - Is the CSS selector outdated? (try None to use generic scraper)

### "I'm getting too much noise"

**Solution:** Improve keyword filtering

1. Add domain-specific keywords to `config.KEYWORDS`
2. Make CSS selectors more specific if possible
3. Check the "Sample of raw items collected" in logs to see what's getting through

### "Specific sites keep failing"

**Options:**
1. Disable the site (comment it out in `config.py`)
2. Request official API access (more reliable than scraping)
3. Check if site's `robots.txt` disallows automated access

---

## Adding a New Source

**General steps:**

1. **Identify the source type:**
   - RSS feed? → add to `DIRECT_RSS_FEEDS`
   - News site without RSS? → add to `SCRAPE_SITES` or `INTERNATIONAL_SOURCES`
   - Research database? → add to `RESEARCH_SOURCES`
   - Government announcement page? → add to `OFFICIAL_SOURCES`

2. **Find the URL and CSS selector:**
   - Visit the site
   - Find the main news/article listing page
   - Right-click a headline → Inspect
   - Note the CSS pattern

3. **Add to `config.py`:**
   ```python
   {
       "name": "Source Name",
       "url": "https://example.com/news/",
       "language": "en",
       "category": "local_online",
       "link_selector": "h2.headline a",  # or None for generic
   }
   ```

4. **Test:**
   - Run a scan
   - Check terminal for "[source_name]: N items"
   - Verify the shortlist includes items from the new source

---

## Configuration Checklist

Before going live with a new configuration:

- [ ] All sources in `config.py` are tested
- [ ] `link_selector` values are accurate (inspect the actual site)
- [ ] Twitter credentials are set up (if using Twitter source)
- [ ] `KEYWORDS` list matches Rwanda health topics
- [ ] Run a full scan and verify output quality
- [ ] Check Sources Dashboard for per-source breakdowns
- [ ] Document any custom sources for future reference
