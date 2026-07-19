# News Sources Summary - What Works & What's Disabled

## 🟢 WORKING LOCAL NEWS SOURCES

### 1. **Google News RSS** (Aggregator - Covers all Rwanda health news)
- **Status:** ✅ WORKING
- **Coverage:** 100-150 items per scan
- **Languages:** English, Kinyarwanda, French
- **Speed:** ~5 seconds
- **Queries used:**
  - "health Rwanda"
  - "Rwanda hospital"
  - "Rwanda disease outbreak"
  - "ubuzima Rwanda" (Kinyarwanda)
  - "sante Rwanda" (French)

### 2. **Direct RSS Feeds** (3 verified outlets)

#### The New Times
- **Status:** ✅ WORKING (VERIFIED)
- **URL:** https://www.newtimes.co.rw/rssFeed/14
- **Language:** English
- **Items per scan:** 30-50
- **Speed:** <1 second

#### KT Press
- **Status:** ✅ WORKING (VERIFIED)
- **URL:** https://www.ktpress.rw/feed/
- **Language:** English
- **Items per scan:** 5-15
- **Speed:** <1 second

#### Taarifa
- **Status:** ✅ WORKING (VERIFIED)
- **URL:** https://www.taarifa.rw/feed/
- **Language:** English/Kinyarwanda
- **Items per scan:** 5-15
- **Speed:** <1 second

### 3. **Web Scrapers** (4 local news sites)

#### Panorama (panorama.rw)
- **Status:** ✅ WORKING
- **Language:** Kinyarwanda
- **Items per scan:** 50-100
- **Speed:** 3-5 seconds
- **Note:** No CSS selector configured - uses generic headline detection

#### The Chronicles (chronicles.rw)
- **Status:** ✅ WORKING
- **Language:** English
- **Items per scan:** 20-40
- **Speed:** 2-3 seconds
- **Note:** No CSS selector configured - uses generic headline detection

#### IGIHE (igihe.com)
- **Status:** ⚠️ OCCASIONALLY BLOCKS (403 Forbidden)
- **Language:** English/Kinyarwanda
- **Items per scan:** 0-50 (when accessible)
- **Speed:** 1-2 seconds
- **Note:** No CSS selector configured - uses generic headline detection

#### Kigali Today (kigalitoday.com)
- **Status:** ⚠️ OCCASIONALLY BLOCKS (403 Forbidden)
- **Language:** Kinyarwanda
- **Items per scan:** 0-30 (when accessible)
- **Speed:** 1-2 seconds
- **Note:** No CSS selector configured - uses generic headline detection

---

## 🔴 DISABLED INTERNATIONAL NEWS SOURCES

These sources are **DISABLED** because they actively block automated requests or cause timeouts.

### Originally Configured (Now Disabled):

1. **Reuters** - HTTP 403 Forbidden
2. **BBC News** - HTTP 403 Forbidden
3. **AFP News** - HTTP 403 Forbidden
4. **Al Jazeera** - HTTP 404 Not Found
5. **France 24** - HTTP 403 Forbidden
6. **DW News** - HTTP 404 Not Found
7. **Africanews** - HTTP 403 Forbidden

### Why Disabled:

- ❌ These major news outlets actively **block web scrapers**
- ❌ Cause **timeouts** and **worker crashes** on Render
- ❌ Google News already aggregates these outlets anyway
- ❌ No benefit to trying to scrape directly

### Alternative:

**Google News already covers international outlets** - your Google News RSS queries include stories from Reuters, BBC, AFP, etc. when they're relevant to Rwanda.

---

## 📊 TYPICAL SCAN OUTPUT

### Collection Numbers (per scan)
```
Google News:        145 items
Direct RSS:          70 items  
Web Scrapers:       100 items
TOTAL COLLECTED:    315 items

After filtering (relevance + dedup):
SHORTLIST:            3-5 stories
```

### Language Breakdown
- **English:** ~60% (Google News, The New Times, KT Press, Chronicle, BBC aggregated)
- **Kinyarwanda:** ~30% (Panorama, IGIHE, Kigali Today, RW Google News)
- **French:** ~10% (French Google News queries)

---

## ✅ SUMMARY TABLE

| Source | Type | Status | Items/Scan | Speed | Languages |
|--------|------|--------|-----------|-------|-----------|
| **Google News** | RSS Aggregator | ✅ Working | 100-150 | 5s | EN/RW/FR |
| **The New Times** | Direct RSS | ✅ Working | 30-50 | <1s | EN |
| **KT Press** | Direct RSS | ✅ Working | 5-15 | <1s | EN |
| **Taarifa** | Direct RSS | ✅ Working | 5-15 | <1s | EN/RW |
| **Panorama** | Web Scraper | ✅ Working | 50-100 | 3-5s | RW |
| **The Chronicles** | Web Scraper | ✅ Working | 20-40 | 2-3s | EN |
| **IGIHE** | Web Scraper | ⚠️ Flaky | 0-50 | 1-2s | EN/RW |
| **Kigali Today** | Web Scraper | ⚠️ Flaky | 0-30 | 1-2s | RW |
| **Reuters** | International | ❌ Disabled | 0 | — | — |
| **BBC** | International | ❌ Disabled | 0 | — | — |
| **AFP** | International | ❌ Disabled | 0 | — | — |
| **Al Jazeera** | International | ❌ Disabled | 0 | — | — |
| **France 24** | International | ❌ Disabled | 0 | — | — |
| **DW News** | International | ❌ Disabled | 0 | — | — |
| **Africanews** | International | ❌ Disabled | 0 | — | — |

---

## 🎯 INTERNATIONAL NEWS COVERAGE

### How You Still Get International Coverage:

**Google News aggregates global outlets** - your searches capture international stories about Rwanda from:
- Reuters
- BBC
- AFP
- Al Jazeera
- France 24
- DW
- Africanews
- And others

**When you scan for:** "Rwanda disease outbreak", "health Rwanda", etc. → Google News returns stories from these international outlets that mention Rwanda.

### Example:
```
Typical Google News result in your scan:
[DR Congo rebels use Ebola response to showcase governance] 
                                          ↑
                                    AnewZ (news aggregator)
                    (but original from Reuters/AFP/etc)
```

---

## 🔧 IF YOU WANT MORE INTERNATIONAL COVERAGE

### Option 1: Use News API (Recommended)
- **Service:** newsapi.org
- **Cost:** Free tier available, $50/month for commercial
- **Benefit:** Reliable, no blocking, structured data
- **Setup:** ~30 minutes to integrate

### Option 2: Add More Local RSS Feeds
- If other Rwanda news outlets have RSS feeds, add them to `DIRECT_RSS_FEEDS`
- Test the feed URL manually first
- Add to config, redeploy

### Option 3: Re-enable International Scrapers (Not Recommended)
- These will cause timeouts on Render
- Only works if you have dedicated infrastructure
- Better to use APIs instead

---

## 📝 CONFIGURATION FILE LOCATIONS

If you want to modify sources:

```
config.py:
  - GOOGLE_NEWS_QUERIES (line ~20)
  - DIRECT_RSS_FEEDS (line ~35)
  - SCRAPE_SITES (line ~60)
  - INTERNATIONAL_SOURCES (line ~85) ← Currently disabled in code
  - OFFICIAL_SOURCES (line ~120) ← Currently disabled in code
  - RESEARCH_SOURCES (line ~150) ← Currently disabled in code
```

---

## 🚀 CURRENT STATE

✅ **Working:** Local sources (Google News + RSS + Web Scrapers)  
❌ **Disabled:** International scrapers (too slow/blocking)  
✅ **Result:** 5-10 second scans, 3-5 relevant stories per day  
✅ **Coverage:** Comprehensive Rwanda health news + international via Google News

This is the optimal setup for **Render free tier** and provides good coverage with zero timeouts.
