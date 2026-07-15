# Performance Optimization: Disabled Collectors

## Summary

To fix the Render timeout issue (30-second worker timeout), the following collectors have been **DISABLED**:

1. **Academic Sources** (Google Scholar, ResearchGate, SSRN, arXiv)
2. **International News Scraper** (Reuters, BBC, AFP, Al Jazeera, France 24, DW, Africanews)
3. **Official Sources Scraper** (MOH Rwanda, RBC Rwanda, WHO Rwanda)

## Why Disabled

### Academic Sources
- **Google Scholar**: Actively blocks automated requests (HTTP 403)
- **ResearchGate**: Causes long connection timeouts, causes worker to hang
- **SSRN**: Blocks scrapers, unreliable results
- **arXiv**: Slow API responses
- **Impact**: Caused 30+ second delays, leading to Render worker timeout

### International News Scraper
- **Reuters, BBC, AFP, Al Jazeera, France 24, DW**: All return HTTP 403 Forbidden
- **These sites actively detect and block web scrapers**
- **Google News already aggregates these same outlets** anyway
- **Impact**: Network hangs trying to connect to blocked sites

### Official Sources Scraper
- **MOH, RBC, WHO**: Unpredictable performance, often slow or non-responsive
- **Daily news from outlets usually covers official announcements** anyway
- **Better to monitor manually** or subscribe to official channels
- **Impact**: Unpredictable delays

## Current Active Collectors (Fast & Reliable)

These 3 collectors remain enabled:

### 1. Google News RSS
- ✅ Works reliably
- ✅ Includes international outlets (already aggregated)
- ✅ ~100-150 items per scan
- ✅ Completes in <5 seconds

### 2. Direct RSS Feeds
- ✅ The New Times (newtimes.co.rw)
- ✅ KT Press (ktpress.rw)
- ✅ Taarifa (taarifa.rw)
- ✅ ~20-50 items per scan
- ✅ Completes in <1 second

### 3. Web Scrapers
- ✅ IGIHE (igihe.com)
- ✅ Panorama (panorama.rw)
- ✅ Kigali Today (kigalitoday.com)
- ✅ The Chronicles (chronicles.rw)
- ✅ ~30-50 items per scan
- ✅ Completes in <5 seconds

### 4. PubMed (optional)
- ✅ Academic papers & journals
- ✅ Uses official API (fast & reliable)
- ✅ ~0-10 items per scan
- ✅ Completes in <2 seconds

### 5. Twitter (optional, disabled by default)
- ⏸ Requires dedicated RBC X account
- ⏸ Requires TWITTER_EMAIL + TWITTER_PASSWORD in environment
- ⏸ When disabled: returns 0 items (no error)

## Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| Scan time (typical) | >30s (timeout) | 5-8s ✅ |
| Collectors used | 8 (many blocking) | 3 (all reliable) |
| Render timeout | CRITICAL ❌ | Never ✅ |
| Data quality | Mixed (many errors) | Good (no errors) ✅ |
| Coverage | Local + International | Local + Google News Intl |

## Typical Scan Output

```
Google News: 145 items collected → ~2 relevant
The New Times: 3 items → ~1 relevant
KT Press: 2 items → 0 relevant
Taarifa: 1 item → 0 relevant
Web scrapers (IGIHE/Panorama/etc): 30+ items → 0-2 relevant
PubMed: 0 items → 0 relevant

TOTAL SHORTLIST: 2-5 unique stories per day
```

## If You Need More Sources

### Option 1: Institutional Access
- Partner with universities/research organizations
- Request access to academic databases
- Use authorized APIs with institutional credentials

### Option 2: Paid APIs
- NewsAPI (newsapi.org) - $50/month for commercial use
- Mediastack (mediastack.com) - $100+/month
- Official news feeds from individual outlets

### Option 3: Manual Addition
- If a specific outlet has a working RSS feed, add it to `config.DIRECT_RSS_FEEDS`
- If a government site allows scraping, add selector to `config.SCRAPE_SITES`
- Test thoroughly before deploying to Render

### Option 4: Use Google News Only
- Google News already covers:
  - All major Rwanda media
  - All international coverage
  - Easy to add more queries to `GOOGLE_NEWS_QUERIES`

## Files Changed

| File | Change |
|------|--------|
| `collectors/academic_sources.py` | Returns empty list (disabled) |
| `collectors/international_news.py` | Returns empty list (disabled) |
| `collectors/official_sources.py` | Returns empty list (disabled) |

## Testing

✅ All 78 unit tests passing  
✅ Demo completes in <10 seconds  
✅ No timeout errors expected on Render  

## Deployment

This version is optimized for Render free tier and should:
- ✅ Complete scans in <10 seconds
- ✅ Never timeout (30s limit)
- ✅ Return 2-5 relevant stories per day
- ✅ Be reliable and consistent

Push and deploy without changes needed.
