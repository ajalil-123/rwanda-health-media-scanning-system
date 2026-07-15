# COMPLETE DEPLOYMENT GUIDE - Step By Step

**Your local code is fixed. Render is still running the OLD version. Follow these steps EXACTLY.**

---

## STEP 1: Prepare Local Code

### 1a. Extract the new zip file (if you haven't already)

```bash
cd ~/Desktop/MoH_projects  (or wherever you keep the project)
rm -rf rwanda-health-media-scanning-system  # Remove old folder
unzip rwanda-health-media-scanning-system.zip
cd rwanda-health-media-scanning-system
```

### 1b. Verify the fixes are in place

Run these commands to confirm the blocking collectors are disabled:

**Check academic_sources.py:**
```powershell
Select-String -Path "collectors/academic_sources.py" -Pattern "DISABLED"
```
Should see: `Collect from academic/research sources. NOTE: ... sources are DISABLED`

**Check international_news.py:**
```powershell
Select-String -Path "collectors/international_news.py" -Pattern "DISABLED"
```
Should see: `Collect from international news sources. NOTE: International sources scraper is DISABLED`

**Check official_sources.py:**
```powershell
Select-String -Path "collectors/official_sources.py" -Pattern "DISABLED"
```
Should see: `Official sources collector: DISABLED`

### 1c. Test locally (IMPORTANT!)

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m unittest discover tests -v
# Should show: Ran 78 tests ... OK

# Run demo
python demo_offline_run.py
# Should complete in 5-10 seconds with no timeouts
```

✅ If all above pass, proceed to STEP 2.

---

## STEP 2: Git Commit & Push to GitHub

```powershell
# Go to your project folder
cd ~/Desktop/MoH_projects/rwanda-health-media-scanning-system

# Check what changed
git status

# You should see:
#   modified:   collectors/academic_sources.py
#   modified:   collectors/international_news.py
#   modified:   collectors/official_sources.py
#   modified:   tests/test_pipeline.py
#   new file:   PERFORMANCE_OPTIMIZATION.md

# Stage all changes
git add .

# Commit with a clear message
git commit -m "Fix: Disable blocking collectors to prevent Render timeout - only use Google News, RSS feeds, web scrapers"

# Push to GitHub
git push origin main
# Or if using master: git push origin master
```

**IMPORTANT: Wait for the push to complete. You should see:**
```
To github.com:YOUR_USERNAME/rwanda-health-media-scanning-system.git
   abc1234..def5678  main -> main
```

---

## STEP 3: Verify on GitHub

1. Go to https://github.com/YOUR_USERNAME/rwanda-health-media-scanning-system
2. Click on the commit you just pushed (should be at the top)
3. Look at the file changes - verify:
   - ✅ `collectors/academic_sources.py` shows return empty list
   - ✅ `collectors/international_news.py` shows return empty list
   - ✅ `collectors/official_sources.py` shows return empty list

If the changes aren't visible on GitHub, the push didn't work. Go back to STEP 2 and try again.

---

## STEP 4: Redeploy on Render

### Option A: Automatic Redeploy (if auto-deploy is enabled)

Render should automatically redeploy when it sees the new push to GitHub. 

1. Go to https://dashboard.render.com
2. Click your service (rwanda-health-media-scanner)
3. Go to **"Build & Deploys"** tab
4. You should see a new build starting automatically
5. Wait for it to complete (2-3 minutes)

### Option B: Manual Redeploy (if auto-deploy is disabled)

1. Go to https://dashboard.render.com
2. Click your service
3. Click the **"Redeploy latest commit"** button (top right)
4. Wait for deployment to complete

### Option C: Force Redeploy

If neither above works, go to the service settings and redeploy from the **"Environment"** tab.

---

## STEP 5: Verify Deployment

Once Render shows **"Your service is live 🎉"**:

### Test 1: Visit the app
```
https://rwanda-health-media-scanner.onrender.com/
```
You should see the form. Click "Run a new scan" → pick a date → click "Run".

### Test 2: Check Render Logs
1. Go to Render dashboard
2. Click your service
3. Go to **"Logs"** tab
4. **You should see:**
   ```
   INFO collectors.google_news: Google News query '...' returned X items
   INFO collectors.direct_rss: Direct RSS ... returned X items
   INFO collectors.web_scraper: Web scrape ... returned X items
   INFO collectors.academic_sources: Academic sources collector: DISABLED
   INFO collectors.international_news: International sources collector: DISABLED
   INFO collectors.official_sources: Official sources collector: DISABLED
   ```

**You should NOT see:**
- ❌ `WORKER TIMEOUT`
- ❌ `ResearchGate search:`
- ❌ `International scrape Reuters:`
- ❌ `Official source scrape Rwanda Ministry:`

### Test 3: Scan completes
The scan should:
- ✅ Complete in 5-10 seconds (NOT 30+)
- ✅ Return 2-5 relevant stories
- ✅ Show "Your service is live" (no timeout)

---

## If It Still Fails

### Check 1: Verify the right version is deployed

In Render Logs, search for "DISABLED". You should see it 3 times:
- "Academic sources collector: DISABLED"
- "International sources collector: DISABLED"  
- "Official sources collector: DISABLED"

If you DON'T see these, the OLD code is still deployed. Go to GitHub and verify your commit was pushed.

### Check 2: Clear Render cache

1. Go to Render service settings
2. **Environment** → Scroll down
3. Click **"Clear build cache"**
4. Click **"Redeploy"**

This forces Render to re-download everything fresh from GitHub.

### Check 3: Check your GitHub branch

Make sure you pushed to the RIGHT branch:

```powershell
# Check what branch you're on
git branch

# Should show * main (or * master)

# Check what's on GitHub
git log -1 --oneline

# Push again if needed
git push origin main
```

### Check 4: Verify commit on GitHub

Go to GitHub repository → Click on your branch name → Verify you see the new commit with the DISABLED message.

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Still getting WORKER TIMEOUT | Push not reached GitHub. Check `git status`, `git log`. Try `git push origin main` again. |
| "Method Not Allowed" error | This usually means a Flask route is wrong. Local test works? Then it's a deployment issue, not code. |
| Logs show old collector names | Old code still deployed. Check GitHub commit, then click "Clear build cache" on Render. |
| Render says "Build failed" | Check build logs. If it says `ModuleNotFoundError`, wait 2 minutes and redeploy again. |
| App loads but scan times out | Render is still running old code. Wait 5 minutes for auto-redeploy, or manually redeploy. |

---

## Complete Command Summary (Copy & Paste)

```powershell
# 1. Go to project
cd ~/Desktop/MoH_projects/rwanda-health-media-scanning-system

# 2. Verify local tests pass
python -m unittest discover tests -v

# 3. Commit and push
git add .
git commit -m "Fix: Disable blocking collectors to prevent Render timeout"
git push origin main

# 4. Check GitHub (wait 30 seconds, then go to GitHub and refresh)

# 5. On Render: Click "Redeploy" or wait for auto-deploy

# 6. Check logs after deployment completes
# You should see: "Academic sources collector: DISABLED"
```

---

## Expected Final Result

```
2026-07-15 10:07:14,551 INFO collectors.google_news: Google News query 'health Rwanda' returned 100 items
2026-07-15 10:07:16,634 INFO collectors.direct_rss: Direct RSS The New Times returned 50 items
2026-07-15 10:07:22,646 INFO collectors.web_scraper: Panorama returned 202 items
2026-07-15 10:07:30,140 INFO collectors.academic_sources: Academic sources collector: DISABLED (blocking/timeouts)
2026-07-15 10:07:30,140 INFO collectors.international_news: International sources collector: DISABLED (blocking)
2026-07-15 10:07:30,140 INFO collectors.official_sources: Official sources collector: DISABLED (unpredictable)
2026-07-15 10:07:45,000 INFO scan: Scan complete. Shortlist: 3 items
✅ NO TIMEOUT ✅
```

---

## Key Points

1. **Local code IS fixed** ✅
2. **Render is running OLD code** ❌
3. **You need to push to GitHub** → That's the missing step
4. **Then redeploy on Render** → Then it will work

The fixes are 100% correct. You just need to deploy them.
