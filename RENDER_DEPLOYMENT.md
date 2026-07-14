# Deploying to Render

This guide explains how to deploy the Rwanda Health Media Scanning System to Render.

## Prerequisites

- A GitHub account with this repository pushed to it
- A Render account (free tier available at render.com)

## Deployment Steps

### 1. Push to GitHub

Make sure your code is pushed to GitHub:

```bash
git add .
git commit -m "Add Rwanda health media scanner"
git push origin main
```

### 2. Connect GitHub to Render

1. Go to [render.com](https://render.com)
2. Sign in with your GitHub account
3. Click "New" → "Web Service"
4. Select "Connect a repository" and choose this repository
5. Click "Connect"

### 3. Configure the Web Service

Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | `rwanda-health-media-scanner` (or your choice) |
| **Environment** | `Python 3` |
| **Region** | Choose closest to you (e.g., `Frankfurt`, `Singapore`) |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -w 1 -b 0.0.0.0:$PORT webapp.app:app` |
| **Plan** | `Free` (or `Starter` for better performance) |

### 4. Environment Variables (Optional)

If you need to add environment variables (e.g., for Twitter authentication), click "Environment" and add:

- `TWITTER_EMAIL`: Your dedicated RBC X account email (if using Twitter collector)
- `TWITTER_PASSWORD`: Your dedicated RBC X account password

Do NOT add these if you're not using the Twitter collector.

### 5. Deploy

Click "Create Web Service" and Render will automatically:
1. Clone your repository
2. Install dependencies from `requirements.txt`
3. Run the web server using gunicorn
4. Make it available at `https://your-app-name.onrender.com`

## Important Notes

### Database

- The app uses SQLite with a file-based database (`media_monitor.db`)
- **WARNING**: Render's free tier uses ephemeral storage, which means the database will be lost when the service restarts
- For persistent data, upgrade to a paid plan or use an external database (PostgreSQL recommended)

### Performance

- Free tier: 0.5 CPU, limited memory
- Best for: Light testing, development
- For production use: Upgrade to Starter or higher plan

### Web Service Lifecycle

Free tier services spin down after 15 minutes of inactivity. On next access, they restart (which takes ~30 seconds).

## Troubleshooting

### "gunicorn: command not found"

This error means `requirements.txt` doesn't have gunicorn. It's been added to the file, but make sure to:
1. Commit the updated `requirements.txt`
2. Push to GitHub
3. Redeploy on Render

### App keeps crashing

Check the logs in Render dashboard:
1. Go to your service
2. Click "Logs"
3. Look for error messages

Common issues:
- Missing Python packages (check `requirements.txt`)
- Database permission issues (free tier file storage is limited)
- Out of memory (upgrade plan or optimize code)

### Database lost after restart

On free tier, all file data is lost when the service restarts. To fix:
1. Upgrade to a paid plan (persistent storage)
2. OR use an external database like Render PostgreSQL

## Local Testing Before Deploying

Test locally with gunicorn before pushing:

```bash
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 webapp.app:app
```

Then visit `http://localhost:5000`

## Production Recommendations

For production use:

1. **Use PostgreSQL** instead of SQLite
   - Render offers free PostgreSQL (limited resources)
   - More reliable than file-based storage

2. **Upgrade Render plan**
   - Free tier has limited memory/CPU
   - Starter ($7/month) or higher recommended

3. **Set up cron jobs for scans**
   - Render doesn't support background jobs on free tier
   - Use an external cron service (EasyCron, AWS Lambda, etc.)

4. **Enable HTTPS** (automatic on Render)
   - Render provides free SSL certificates

5. **Monitor logs**
   - Set up alerts for failures
   - Use Render's built-in log view

## Updating the Deployment

After making code changes:

```bash
git add .
git commit -m "Fix: description of changes"
git push origin main
```

Render will automatically redeploy (if auto-deploy is enabled).

## Disabling Auto-Deploy

If you don't want automatic deploys on every push:
1. Go to your Render service
2. Settings → Auto-Deploy
3. Disable

Then you can manually trigger deploys from the Render dashboard.

## Getting Help

- Render docs: https://render.com/docs
- Deployment issues: Check the Logs in your Render dashboard
- This app issues: Check terminal output or README.md
