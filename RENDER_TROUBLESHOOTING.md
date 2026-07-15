# Render Deployment Troubleshooting & Verification Checklist

## Before Deploying to Render

### Step 1: Verify Locally First

Run these commands in your local environment to confirm everything works:

```bash
# 1. Extract the new zip
unzip rwanda-health-media-scanning-system.zip
cd rwanda-health-media-scanning-system

# 2. Install ALL dependencies (including gunicorn)
pip install -r requirements.txt

# 3. Run unit tests (should be 78 passing)
python -m unittest discover tests -v

# 4. Run the demo (simulates a scan)
python demo_offline_run.py

# 5. Start the web app and test manually
python webapp/app.py
# Visit http://localhost:5000
# Click "Run a new scan" → pick "daily" mode → pick a date → click "Run"
# It should complete successfully (even if 0 items, no error)
```

✅ **If all above pass**, your code is ready for Render.

---

## Deploying to Render

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Fix: academic sources and Render deployment"
git push origin main
```

### Step 3: Connect to Render

1. Go to https://render.com
2. Click **"New"** → **"Web Service"**
3. Select your repository
4. Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | `rwanda-health-media-scanner` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -w 1 -b 0.0.0.0:$PORT webapp.app:app` |
| **Plan** | `Free` (or Starter for better performance) |

4. Click **"Create Web Service"**
5. Wait for deployment (2-3 minutes)

---

## If Render Deployment Fails

### Check the Logs

**In Render dashboard:**
1. Go to your service
2. Click **"Logs"** tab
3. Look for error messages at the bottom

### Common Errors & Solutions

#### Error: `bash: line 1: gunicorn: command not found`
- **Cause:** Old `requirements.txt` without gunicorn
- **Solution:** 
  1. Verify your `requirements.txt` has: `gunicorn>=22.0.0`
  2. Commit and push to GitHub
  3. In Render, click "Redeploy" (or delete and recreate the service)

#### Error: `ModuleNotFoundError: No module named 'collectors'`
- **Cause:** Working directory issue
- **Solution:**
  1. Make sure `Procfile` has: `web: gunicorn -w 1 -b 0.0.0.0:$PORT webapp.app:app`
  2. The app must start from the repo root (where `collectors/`, `webapp/`, `Procfile` are)

#### Error: `Address already in use` or port errors
- **Cause:** Render's PORT environment variable not being used
- **Solution:**
  1. Verify `webapp/app.py` has this code at the bottom:
     ```python
     if __name__ == "__main__":
         import os
         db.init_db()
         port = int(os.environ.get("PORT", 5000))
         app.run(debug=False, host="0.0.0.0", port=port)
     ```
  2. Make sure `Procfile` uses `$PORT` (not hardcoded 5000)

#### Error: `Internal Server Error` when visiting the app
- **Check these in Render Logs:**
  1. Is the app starting? Look for `Running on http://...`
  2. Are there tracebacks? Post them here for debugging
  3. Check if database is being created: should see `init_db` messages

---

## Testing the Deployed App

Once Render deployment succeeds:

1. **Visit your app:** `https://your-app-name.onrender.com`
2. **You should see:** The scan form with "Run a new scan"
3. **Test a scan:**
   - Pick "daily" mode
   - Pick today's date (or any date)
   - Click "Run"
   - Should redirect to results (even if 0 items, no error)

4. **If you get Internal Server Error:**
   - Check Render Logs for the actual error
   - Copy the error message
   - Share it for debugging

---

## What the Fixes Do

### Fix #1: Academic Sources Collector
- Removed invalid `user_agent` parameter (was crashing)
- Fixed arXiv URL encoding (was creating malformed URLs)
- **Impact:** Scans no longer crash when academic sources run

### Fix #2: DateTime Type Handling
- Scrapers now return datetime objects (not strings)
- Database properly converts to strings for storage
- **Impact:** Date filtering now works correctly

### Fix #3: Render Support
- Added `gunicorn` to `requirements.txt`
- Created `Procfile` with proper startup command
- Updated app to read `PORT` from environment
- **Impact:** App can start on Render and listen on the right port

---

## Quick Verification

Before deploying, verify these files exist and have the right content:

### `requirements.txt`
Should include:
```
requests>=2.28
flask>=3.0
python-docx>=1.1
beautifulsoup4>=4.12
twikit>=1.0.0
gunicorn>=22.0.0
```

### `Procfile`
Should contain:
```
web: gunicorn -w 1 -b 0.0.0.0:$PORT webapp.app:app
```

### `webapp/app.py` (bottom of file)
Should have:
```python
if __name__ == "__main__":
    import os
    db.init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
```

### `collectors/academic_sources.py` (line ~35)
Should **NOT** have `user_agent=` parameter:
```python
html = fetch_url(url)  # ✓ Correct
# NOT: fetch_url(url, user_agent="...") ✗ Wrong
```

---

## If It Still Fails on Render

**Collect this info and share it:**

1. **Render error message** (from Logs tab)
2. **Your `requirements.txt`** content
3. **Your `Procfile`** content
4. **The Render build log** (from "Build & Deploys" tab)

With that info, I can debug the exact issue.

---

## Development vs Production

| Aspect | Dev (VS Code) | Production (Render) |
|--------|---------------|-------------------|
| Port | 5000 (hardcoded) | $PORT env var |
| Database | `media_monitor.db` (ephemeral on Render) | Same file |
| Debug mode | On | Off (`debug=False`) |
| Host | localhost | 0.0.0.0 (all interfaces) |

The fixes align your code with production requirements.

---

## One More Thing

If Render keeps failing and you want to test with gunicorn locally first:

```bash
# Install gunicorn if not already installed
pip install gunicorn

# Test the app with gunicorn (like Render will run it)
gunicorn -w 1 -b 0.0.0.0:5000 webapp.app:app

# Visit http://localhost:5000
# Test a scan
# Stop with Ctrl+C
```

If this works locally, it will work on Render.
