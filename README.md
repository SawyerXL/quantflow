# QuantFlow

Quantitative backtesting SaaS platform. Build, test, and deploy algorithmic trading strategies.

## Tech Stack

- **Frontend**: Next.js 14 (App Router) + TypeScript + TailwindCSS
- **Backend**: FastAPI + Python 3.11
- **Database**: PostgreSQL (Supabase) + Redis (Upstash)
- **Backtesting Engine**: pandas + numpy + lightweight-charts
- **Payments**: Stripe
- **Deployment**: Vercel + Render (full free-tier, $0/mo)

## Quick Start

```bash
# Copy environment variables
cp .env.example .env

# Start all services locally
docker compose up -d
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
quantflow/
├── frontend/              # Next.js 14 frontend
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   └── lib/               # Utilities & API client
├── backend/               # FastAPI backend
│   └── app/
│       ├── api/           # Route handlers
│       ├── core/          # Config, auth, database
│       ├── models/        # SQLAlchemy models
│       ├── schemas/       # Pydantic schemas
│       └── services/      # Business logic
├── scripts/               # Setup guides
├── docker-compose.yml     # Local dev environment
└── DEPLOY.md              # Free deployment guide ($0/mo)
```

## Environment Variables

See `.env.example` for all required environment variables.

## Deployment

See [DEPLOY.md](DEPLOY.md) for the complete 12-step, 30-minute free deployment guide.
