# Bug Fixes - Rwanda Health Media Scanning System

## Fixes Applied

### 1. **Academic Sources Collector Errors** ✅ FIXED
**Problem:** The system crashed with errors when the academic sources collector ran.

**Errors fixed:**
- `fetch_url() got an unexpected keyword argument 'user_agent'`
  - **File:** `collectors/academic_sources.py`
  - **Cause:** `scrape_google_scholar()` was passing `user_agent` parameter that `fetch_url()` doesn't accept
  - **Fix:** Removed the `user_agent` parameter (fetch_url uses default headers)

- `URL can't contain control characters` (arXiv)
  - **File:** `collectors/academic_sources.py`
  - **Cause:** `scrape_arxiv()` was not URL-encoding the search query, so spaces were being passed directly to the URL
  - **Fix:** Added `urllib.parse.quote()` to properly encode the query parameter

### 2. **Render Deployment** ✅ FIXED
**Problem:** Render deployment failed with `gunicorn: command not found`

**Fixes:**
- Added `gunicorn>=22.0.0` to `requirements.txt`
- Created `Procfile` with Render startup command
- Created `render.yaml` with deployment configuration
- Updated `webapp/app.py` to support production environment variables
- Created `RENDER_DEPLOYMENT.md` with comprehensive deployment guide

### 3. **DateTime Type Mismatch** ✅ FIXED  
**Problem:** Error when date extraction returned ISO strings instead of datetime objects

**Fixes:**
- Updated `collectors/web_scraper.py` to return datetime objects (not ISO strings)
- Updated `collectors/international_news.py` to return datetime objects
- Updated `collectors/official_sources.py` to return datetime objects
- Updated `db.insert_item()` to convert datetime objects to ISO strings only when storing

---

## Testing Status

All 78 unit tests: **PASSING** ✅

---

## What to Do Now

1. **Extract the updated zip file**
2. **For Render deployment:** Read `RENDER_DEPLOYMENT.md`
3. **For local use:** Run `python webapp/app.py`
4. **Scan for specific dates:** Should now work without "Internal Server Error"

---

## Files Changed

| File | Change |
|------|--------|
| `collectors/academic_sources.py` | Removed invalid `user_agent` parameter; fixed arXiv URL encoding |
| `collectors/web_scraper.py` | Return datetime objects (not ISO strings) |
| `collectors/international_news.py` | Return datetime objects (not ISO strings) |
| `collectors/official_sources.py` | Return datetime objects (not ISO strings) |
| `db.py` | Handle datetime-to-string conversion when storing |
| `webapp/app.py` | Support production PORT environment variable |
| `requirements.txt` | Added gunicorn |
| `Procfile` | NEW - Render startup configuration |
| `render.yaml` | NEW - Render service configuration |
| `RENDER_DEPLOYMENT.md` | NEW - Comprehensive deployment guide |

---

## Known Limitations

On Render free tier:
- Database (SQLite file) is ephemeral and deleted on service restart
- For production: upgrade to paid plan or use external PostgreSQL database
