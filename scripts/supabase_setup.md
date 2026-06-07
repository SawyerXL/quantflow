# Supabase Database Setup

Supabase free tier: 500 MB database, 2 projects, auto-backups.

---

## Step 1: Create Project

1. Go to [supabase.com](https://supabase.com) → Sign Up
2. **New Project** → Fill in:
   - Name: `quantflow`
   - Database Password: **Generate a strong password** (save it!)
   - Region: `US East (N. Virginia)` — closest to Render Oregon
   - Pricing Plan: Free
3. Wait ~2 minutes for provisioning

## Step 2: Get Connection String

Go to **Settings → Database**:

You'll see two connection modes:

### Connection Pooling (Transaction Mode) **← Use This**
```
postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```
- Port **6543** — PgBouncer connection pooler
- Required for Render free tier (limited connections)
- Mode: Transaction (each transaction gets a connection)

### Direct Connection (Session Mode)
```
postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```
- Port **5432** — Direct to PostgreSQL
- Only use for migrations (alembic)

## Step 3: Configure Environment

Add to Render environment variables or local `.env`:

```bash
# For the app (async — uses pooler)
DATABASE_URL=postgresql+asyncpg://postgres.YOUR_REF:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# For migrations (uses direct connection)
DATABASE_URL_SYNC=postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

**Important**: Replace `YOUR_REF` and `YOUR_PASSWORD` with actual values.

## Step 4: Run Migrations

```bash
# From the backend directory
cd backend

# Apply migrations
alembic -c alembic.ini upgrade head

# Verify tables exist
# Go to Supabase → Table Editor → you should see: users, strategies, backtest_results
```

## Step 5: Supabase Dashboard Features

Free tier includes:
- **Table Editor**: View/edit data visually
- **SQL Editor**: Run ad-hoc queries
- **Database Backups**: Automatic daily
- **API**: Auto-generated REST API (disabled — we use our own)
- **Auth**: Not used (we use JWT with bcrypt)

## Connection Limits

| Resource | Free Tier Limit |
|----------|----------------|
| Database size | 500 MB |
| Direct connections | 15 |
| Pooler connections | 60 |
| Projects | 2 |

Our `database.py` configures `pool_size=3, max_overflow=0` to stay within limits.
