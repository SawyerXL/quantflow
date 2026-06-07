# QuantFlow

Quantitative backtesting SaaS platform. Build, test, and deploy algorithmic trading strategies.

## Tech Stack

- **Frontend**: Next.js 14 (App Router) + TypeScript + TailwindCSS
- **Backend**: FastAPI + Python 3.11
- **Database**: PostgreSQL + Redis
- **Backtesting Engine**: vectorbt + pandas + numpy
- **Payments**: Stripe

## Quick Start

```bash
# Copy environment variables
cp .env.example .env

# Start all services
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
└── docker-compose.yml     # Local dev environment
```

## Environment Variables

See `.env.example` for all required environment variables.
