# AAPL Price Dashboard - Deployment Guide

This guide provides step-by-step instructions for deploying the AAPL price monitoring dashboard.

## Overview

The deployment consists of:
1. **Frontend Dashboard** (`dashboard.html`) - Displays price data and alerts
2. **Pipeline Script** (`run_pipeline.py`) - Fetches prices and detects alerts
3. **GitHub Actions** (`.github/workflows/weekly-update.yml`) - Automated weekly execution
4. **Netlify Deployment** - Hosts the dashboard

## Prerequisites

- GitHub account with access to the repository
- Polygon.io API key (free tier available at https://polygon.io)
- Netlify account (free tier available at https://netlify.com)

## Step 1: Set Up GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add the following secret:
   - Name: `POLYGON_API_KEY`
   - Value: Your Polygon.io API key
5. Click **Add secret**

## Step 2: Test Pipeline Locally (Optional)

Before deploying, you can test the pipeline locally:

```bash
# Export your API key
export POLYGON_API_KEY="your_api_key_here"

# Install dependencies
pip install httpx pandas pyarrow

# Run the pipeline
python run_pipeline.py
```

Expected output:
- `data/prices_state.json` updated with latest AAPL prices
- `data/alerts.json` updated with alert status
- Git commit created: "chore: weekly price update [AAPL]"

## Step 3: Deploy to Netlify

### Option A: Deploy via Netlify UI

1. Log in to [Netlify](https://app.netlify.com)
2. Click **Add new site** > **Import an existing project**
3. Choose **GitHub** and authorize Netlify
4. Select your repository (`edgartools`)
5. Configure build settings:
   - **Build command**: (leave empty - no build needed)
   - **Publish directory**: `.` (root directory)
6. Click **Deploy site**
7. Wait for deployment to complete
8. Your dashboard will be live at `https://[random-name].netlify.app/dashboard.html`

### Option B: Deploy via Netlify CLI

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login to Netlify
netlify login

# Initialize site
netlify init

# Deploy
netlify deploy --prod
```

### Custom Domain (Optional)

1. In Netlify dashboard, go to **Site settings** > **Domain management**
2. Click **Add custom domain**
3. Follow instructions to configure DNS

## Step 4: Verify GitHub Actions Workflow

1. Go to your GitHub repository
2. Navigate to **Actions** tab
3. You should see the workflow **Weekly AAPL Price Update**
4. To test immediately, click **Run workflow** (don't wait for Monday 8 AM UTC)
5. Monitor the workflow execution:
   - ✅ Checkout repository
   - ✅ Set up Python
   - ✅ Install dependencies
   - ✅ Run pipeline
   - ✅ Push changes
6. Verify that new commits appear in your repository

## Step 5: End-to-End Verification

### Test 1: Manual Pipeline Run

```bash
export POLYGON_API_KEY="your_api_key"
python run_pipeline.py
```

Expected result: Exit code 0, files updated, git commit created

### Test 2: Dashboard Display

1. Open dashboard in browser: `https://[your-site].netlify.app/dashboard.html`
2. Verify the following elements display correctly:
   - ✅ AAPL ticker and title
   - ✅ Alert status (🟢 GREEN or 🔴 RED)
   - ✅ 7 days ago price
   - ✅ Latest close price
   - ✅ Price change percentage
   - ✅ Last updated timestamp

### Test 3: Alert Simulation

To test the alert system manually:

1. Edit `data/prices_state.json` to create a >5% drop:

```json
{
  "timestamp": "2024-01-07T00:00:00",
  "prices": [
    {"date": "2024-01-01", "close": 200.0, "volume": 1000000},
    {"date": "2024-01-02", "close": 198.0, "volume": 1100000},
    {"date": "2024-01-03", "close": 195.0, "volume": 1200000},
    {"date": "2024-01-04", "close": 192.0, "volume": 1300000},
    {"date": "2024-01-05", "close": 189.0, "volume": 1400000}
  ],
  "last_fetch_timestamp": "2024-01-05T00:00:00"
}
```

2. Run alert detection:

```bash
python -c "from edgar.polygon import detect_price_drop_alert; detect_price_drop_alert()"
```

3. Check `data/alerts.json`:

```json
{
  "alert_triggered": true,
  "price_first_close": 200.0,
  "price_last_close": 189.0,
  "drop_percentage": 5.5,
  "reason": "price_drop_5.50%"
}
```

4. Refresh dashboard → Should show 🔴 RED alert

### Test 4: GitHub Actions Schedule

- The workflow runs every **Monday at 8:00 AM UTC**
- To verify without waiting, manually trigger via **Actions** > **Weekly AAPL Price Update** > **Run workflow**
- Check the Actions log for successful execution
- Verify dashboard updates automatically after workflow completes

## Troubleshooting

### Pipeline Fails with "POLYGON_API_KEY not set"

- Ensure the secret is added in GitHub repository settings
- For local testing, ensure `export POLYGON_API_KEY="..."` is run in your shell

### Dashboard Shows "Failed to load data files"

- Check that `data/prices_state.json` and `data/alerts.json` exist in the repository
- Verify Netlify is deploying from the correct directory
- Check browser console (F12) for detailed error messages

### GitHub Actions Workflow Doesn't Run

- Verify the workflow file is at `.github/workflows/weekly-update.yml`
- Check that the repository has Actions enabled (Settings > Actions > General)
- Ensure `POLYGON_API_KEY` secret is set

### Git Push Fails in GitHub Actions

- Ensure the workflow has write permissions:
  - Go to **Settings** > **Actions** > **General**
  - Under **Workflow permissions**, select **Read and write permissions**
  - Click **Save**

## Monitoring & Maintenance

### View Logs

- **GitHub Actions**: Repository > Actions tab > Select workflow run
- **Netlify**: Site dashboard > Deploys > Deploy log
- **Local errors**: Check `~/fetch_errors.log`

### Update Schedule

To change the cron schedule, edit `.github/workflows/weekly-update.yml`:

```yaml
on:
  schedule:
    - cron: '0 8 * * 1'  # Monday 8 AM UTC
    # Examples:
    # - cron: '0 9 * * 1-5'  # Weekdays 9 AM UTC
    # - cron: '0 */6 * * *'  # Every 6 hours
```

### Data Retention

- Price data is stored in Git history
- Alert history can be tracked via Git commits
- Netlify caches data files for 5 minutes (configurable in `netlify.toml`)

## Security Notes

- ✅ API key stored as GitHub secret (not in code)
- ✅ All data fetching happens server-side (GitHub Actions)
- ✅ Dashboard is read-only (no API keys exposed)
- ✅ CORS headers configured for data access

## Support

For issues or questions:
1. Check GitHub Actions logs for pipeline errors
2. Review Netlify deploy logs for hosting issues
3. Inspect browser console (F12) for frontend errors
4. Check `~/fetch_errors.log` for API errors

## Next Steps

- [ ] Set up custom domain for dashboard
- [ ] Add email/Slack notifications for alerts
- [ ] Extend to monitor multiple tickers
- [ ] Add historical price charts
- [ ] Implement user-configurable alert thresholds
