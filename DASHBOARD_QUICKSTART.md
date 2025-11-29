# Dashboard Quick Start Guide

Get your AAPL price monitoring dashboard up and running in 5 minutes.

## Prerequisites

- GitHub account
- Polygon.io API key ([Get free key](https://polygon.io/dashboard/signup))
- Netlify account (optional, for hosting)

## Step 1: Set API Key Secret (2 minutes)

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `POLYGON_API_KEY`
5. Value: Paste your Polygon.io API key
6. Click **Add secret**

## Step 2: Enable GitHub Actions (30 seconds)

1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select **Read and write permissions**
3. Click **Save**

## Step 3: Test the Workflow (1 minute)

1. Go to **Actions** tab
2. Click **Weekly AAPL Price Update** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait ~30 seconds for completion
5. Verify green checkmark ✅

## Step 4: Deploy to Netlify (2 minutes)

### Quick Deploy Button

[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/dgunning/edgartools)

### Manual Deploy

1. Log in to [Netlify](https://app.netlify.com)
2. Click **Add new site** → **Import an existing project**
3. Choose **GitHub** and select your repository
4. Build settings:
   - Build command: (leave empty)
   - Publish directory: `.`
5. Click **Deploy site**

## Step 5: View Your Dashboard (10 seconds)

1. Once deployed, click **Open production deploy** in Netlify
2. Dashboard auto-loads at `https://[your-site].netlify.app/`
3. You should see:
   - 🟢 or 🔴 alert status
   - Latest AAPL close price
   - 7-day price change percentage
   - Last updated timestamp

## Troubleshooting

### ❌ Workflow fails with "POLYGON_API_KEY not set"

**Solution**: Go to Settings → Secrets → Actions and add `POLYGON_API_KEY` secret

### ❌ Dashboard shows "Failed to load data files"

**Solution**: 
1. Run the workflow manually (Actions → Weekly AAPL Price Update → Run workflow)
2. Ensure `data/prices_state.json` and `data/alerts.json` exist in repo
3. Clear browser cache and refresh

### ❌ Git push fails in workflow

**Solution**: Go to Settings → Actions → General → Enable "Read and write permissions"

## Testing Alert System

Want to see a 🔴 RED alert? Edit `data/prices_state.json` manually:

```json
{
  "timestamp": "2024-01-07T00:00:00",
  "prices": [
    {"date": "2024-01-01", "close": 200.0, "volume": 1000000},
    {"date": "2024-01-05", "close": 189.0, "volume": 1400000}
  ],
  "last_fetch_timestamp": "2024-01-05T00:00:00"
}
```

Then run:
```bash
python -c "from edgar.polygon import detect_price_drop_alert; detect_price_drop_alert()"
```

Refresh dashboard → Should show 🔴 RED alert (5.5% drop)

## Customization

### Change Update Schedule

Edit `.github/workflows/weekly-update.yml`:

```yaml
schedule:
  - cron: '0 8 * * 1'  # Monday 8 AM UTC
```

Examples:
- `'0 9 * * 1-5'` - Weekdays at 9 AM UTC
- `'0 */6 * * *'` - Every 6 hours
- `'0 0 * * 0'` - Sundays at midnight UTC

### Change Alert Threshold

Edit `edgar/polygon.py`, line 378:

```python
alert_triggered = drop_percentage >= 5.0  # Change 5.0 to your threshold
```

### Monitor Different Tickers

Edit `run_pipeline.py` to call `fetch_aapl_prices('TSLA', 7)` instead

## Next Steps

- ✅ Set up custom domain in Netlify
- ✅ Add email notifications (use GitHub Actions email step)
- ✅ Monitor multiple stocks
- ✅ Add price charts using Chart.js

## Support

- 📖 [Full Deployment Guide](DEPLOYMENT.md)
- 🐛 [Report Issues](https://github.com/dgunning/edgartools/issues)
- 💬 [Ask Questions](https://github.com/dgunning/edgartools/discussions)
