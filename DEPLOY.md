# QuantFlow — Free Deployment Guide

Deploy the entire QuantFlow stack for **$0/month** using free tiers.  
Total setup time: ~30 minutes.

---

## Architecture (All Free)

| Service | Provider | Free Tier Limits |
|---------|----------|-----------------|
| Frontend | **Vercel** | 100 GB bandwidth, 6,000 build-minutes |
| Backend | **Render** | 750 hours/month, spins down after 15 min idle |
| Database | **Supabase** | 500 MB, 2 projects, auto-backups |
| Redis Cache | **Upstash** | 10,000 commands/day, 256 MB |
| File Storage | **Cloudflare R2** | 10 GB, 10M reads/month, 1M writes/month |
| Email | **Resend** | 100 emails/day |
| Error Tracking | **Sentry** | 5,000 errors/month |
| Keep-Alive | **Cron-Job.org** | Free, unlimited cron jobs |
| CDN / DNS | **Cloudflare** | Free, unlimited |

---

## Step 1: Supabase Database (5 min)

1. Sign up at [supabase.com](https://supabase.com)
2. Create a new project named `quantflow`
3. Save the database password
4. Go to **Settings → Database** → copy the **pooler connection string** (port 6543)
5. See `scripts/supabase_setup.md` for detailed instructions

**Connection string format:**
```
postgresql+asyncpg://postgres.YOUR_REF:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

## Step 2: Upstash Redis (3 min)

1. Sign up at [upstash.com](https://upstash.com)
2. Create a new Redis database → select **Global** region
3. Copy the **REST URL** and **REST Token** from the dashboard
4. Keep the tab open — you'll need these for Render env vars

## Step 3: Cloudflare R2 (5 min)

1. Sign up at [cloudflare.com](https://cloudflare.com)
2. Go to **R2** → **Create Bucket** → name it `quantflow-uploads`
3. Go to **Manage R2 API Tokens** → **Create API Token**
   - Permission: **Object Read & Write**
   - Select the `quantflow-uploads` bucket
4. Copy: **Access Key ID**, **Secret Access Key**, **Endpoint URL**

## Step 4: Resend Email (3 min)

1. Sign up at [resend.com](https://resend.com)
2. Go to **API Keys** → **Create API Key**
3. Copy the key (starts with `re_`)
4. Optional: Add your domain under **Domains** (required for production)

## Step 5: Stripe Payments (5 min)

1. Sign up at [stripe.com](https://stripe.com)
2. Switch to **Test Mode** (toggle in dashboard sidebar)
3. Go to **Developers → API Keys** → copy **Secret Key** (`sk_test_...`)
4. Go to **Products** → create:
   - **QuantFlow Pro Monthly** ($19/mo) → copy Price ID
   - **QuantFlow Pro Yearly** ($159/yr) → copy Price ID
   - **QuantFlow Quant Monthly** ($49/mo) → copy Price ID
   - **QuantFlow Quant Yearly** ($399/yr) → copy Price ID
5. Go to **Developers → Webhooks** → add endpoint:
   - URL: `https://quantflow-api.onrender.com/api/v1/billing/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
   - Copy the **Webhook Signing Secret** (`whsec_...`)

## Step 6: Sentry Error Monitoring (2 min)

1. Sign up at [sentry.io](https://sentry.io)
2. Create a new project → **FastAPI** (for backend) + **Next.js** (for frontend)
3. Copy both DSN URLs

## Step 7: Deploy Backend to Render (10 min)

1. Sign up at [render.com](https://render.com) and connect your GitHub account
2. Click **New → Web Service** → select your QuantFlow repository
3. Configure:
   - **Name**: `quantflow-api`
   - **Root Directory**: `backend`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**
4. Add **Environment Variables** (copy from `.env.example`):
   - All `DATABASE_URL`, `UPSTASH_*`, `R2_*`, `JWT_SECRET`, `STRIPE_*`, `RESEND_API_KEY`, `SENTRY_DSN`
5. Click **Deploy Web Service**
6. Wait ~5 minutes for the first build
7. Verify: open `https://quantflow-api.onrender.com/health` → should return `{"status": "ok"}`
8. **Alt**: Push `backend/render.yaml` and use Render Blueprint (auto-deploy)

## Step 8: Run Database Migrations

From your local machine (with the Supabase connection string):

```bash
cd backend
pip install alembic asyncpg
DATABASE_URL="postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
alembic -c alembic.ini upgrade head
```

This creates the `users`, `strategies`, and `backtest_results` tables.

## Step 9: Set Up Keep-Alive (2 min)

Render free tier spins down after 15 minutes of inactivity.

1. Sign up at [cron-job.org](https://cron-job.org)
2. Create a cron job:
   - **URL**: `https://quantflow-api.onrender.com/health`
   - **Interval**: Every 14 minutes
   - **Method**: GET
3. See `scripts/keep_alive_setup.md` for details

## Step 10: Deploy Frontend to Vercel (5 min)

1. Sign up at [vercel.com](https://vercel.com) and connect GitHub
2. Click **Add New → Project** → select your QuantFlow repo
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js
   - **Build Command**: `next build`
   - **Output Directory**: `.next`
4. Add **Environment Variables**:
   - `NEXT_PUBLIC_API_URL` = `https://quantflow-api.onrender.com/api/v1`
   - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` = `pk_live_...`
   - `NEXT_PUBLIC_SENTRY_DSN` = Sentry DSN
5. Click **Deploy**
6. Wait ~2 minutes for the build
7. Vercel gives you a `.vercel.app` domain

## Step 11: Custom Domain (Optional, ~$1/year)

1. Buy a domain at [namesilo.com](https://namesilo.com) (`.xyz` domains ~$1/year)
2. Go to [Cloudflare](https://cloudflare.com) → **Add Site** → enter your domain
3. Update nameservers at NameSilo to Cloudflare's
4. In Cloudflare DNS, add:
   - **CNAME** `@` → `cname.vercel-dns.com` (Vercel)
   - **CNAME** `www` → `cname.vercel-dns.com`
5. In Vercel → Project Settings → Domains → add your custom domain

## Step 12: Verify Everything

- [ ] Visit your Vercel URL — landing page loads
- [ ] Register a new account
- [ ] Run a backtest (enter AAPL, MA Crossover)
- [ ] Results page shows metrics and charts
- [ ] `/health` returns 200 from Render
- [ ] Stripe checkout loads (test mode)
- [ ] Sentry dashboard shows events

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Render returns 503 | Cold start — wait 30s and retry (frontend auto-retries) |
| Backend 500 error | Check Render logs → Look for env var issues |
| Database connection refused | Verify Supabase pooler URL uses port 6543 |
| Upstash commands exhausted | Wait until next day (resets at midnight UTC) |
| Vercel build fails | Check that `next.config.js` has `output: "standalone"` |
| Stripe webhook fails locally | Use Stripe CLI: `stripe listen --forward-to localhost:8000/api/v1/billing/webhook` |

---

## Monthly Cost Summary

| Service | Cost |
|---------|------|
| Vercel | $0 |
| Render | $0 |
| Supabase | $0 |
| Upstash | $0 |
| Cloudflare R2 | $0 |
| Resend | $0 |
| Cron-Job.org | $0 |
| Sentry | $0 |
| Stripe | $0 (test mode) / 2.9% + $0.30 per transaction (live) |
| **TOTAL** | **$0/month** |

When you start getting paying customers, the first upgrade should be Render ($19/month)  
to remove the 15-minute sleep and cold starts.
