# Render Free Tier — Keep-Alive Setup

Render's free tier **spins down after 15 minutes of inactivity**.  
Cold start takes ~30 seconds on first request.

Use **Cron-Job.org** (free) to ping the health endpoint every 14 minutes.

---

## Step-by-Step

### 1. Register
Go to [cron-job.org](https://cron-job.org) and sign up (free, no credit card).

### 2. Create a new cron job
- **Title**: QuantFlow Keep-Alive
- **URL**: `https://quantflow-api.onrender.com/health`
- **Interval**: Every 14 minutes
- **Request Method**: GET
- **Timeout**: 30 seconds

### 3. Advanced Settings (optional)
- **Save response**: unchecked (saves quota)
- **Retry on failure**: checked, 2 retries at 1-minute intervals

### 4. Save & Monitor
Check the "Execution History" tab after a few hours to verify pings are succeeding.

---

## How It Works

```
Cron-Job.org                Render
    │                         │
    ├─ GET /health ──────────►│  (every 14 min)
    │                         │
    │◄─ 200 {"status":"ok"} ──┤
    │                         │
   [14 min wait]              │
    │                         │
    ├─ GET /health ──────────►│
    │                         │
```

The health endpoint also checks database connectivity.  
If the database is unreachable, it returns `{"status": "ok", "database": "unreachable"}` —  
the HTTP status is still 200 so Render doesn't flag it as unhealthy.

---

## Alternative: UptimeRobot

[uptimerobot.com](https://uptimerobot.com) also offers free monitoring with 5-minute intervals.  
Set up an HTTP monitor pointing at `https://quantflow-api.onrender.com/health`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cron job fails | Render is deploying | Wait 2 min, retry |
| Cold start > 60s | Free tier resource limits | Accept; frontend retries handle this |
| 503 Service Unavailable | Render monthly hours exceeded (750h) | Upgrade to starter plan or wait until next month |
