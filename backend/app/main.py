"""
QuantFlow FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.models import User, Strategy, BacktestResult  # noqa: F401 — register models
from app.api.routes import auth, backtest, data, billing, dashboard, share, optimization

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Sentry (error monitoring) ────────────────────────────────────────────────
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.05,  # Free tier: only capture 5% of traces
        environment="production" if not settings.DEBUG else "development",
        # Don't trace health check pings (wastes quota)
        traces_sampler=lambda ctx: (
            0.0
            if ctx.get("asgi_scope", {}).get("path") == "/health"
            else 0.05
        ),
        # Filter low-value errors
        ignore_errors=[KeyboardInterrupt],
    )
    logger.info("Sentry initialized")


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# ── App ──────────────────────────────────────────────────────────────────────


app = FastAPI(
    title=settings.APP_NAME,
    description="Quantitative backtesting SaaS platform — build, test, "
    "and deploy algorithmic trading strategies.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication — register, login, token refresh."},
        {"name": "Backtest", "description": "Run and manage backtests."},
        {"name": "Data", "description": "Market data, CSV parsing, ticker validation."},
        {"name": "Billing", "description": "Subscription plans and checkout."},
    ],
)


# ── Middleware: unified error format ─────────────────────────────────────────


class UnifiedErrorMiddleware(BaseHTTPMiddleware):
    """Wraps all responses in the unified {success, data|error} format.

    Catches unhandled exceptions and returns them as:
        {"success": false, "error": {"code": "server.error", "message": "..."}}
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except HTTPException as exc:
            detail = exc.detail
            if isinstance(detail, dict) and "code" in detail and "message" in detail:
                body = {"success": False, "error": detail}
            else:
                body = {
                    "success": False,
                    "error": {
                        "code": "server.error",
                        "message": str(detail) if detail else "An error occurred",
                    },
                }
            return JSONResponse(status_code=exc.status_code, content=body)
        except Exception as exc:
            logger.exception("Unhandled exception on %s %s", request.method, request.url)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "server.error",
                        "message": f"{type(exc).__name__}: {exc}",
                    },
                },
            )
        return response


app.add_middleware(UnifiedErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://quantflow-two.vercel.app",
        "https://quantflow.pages.dev",
        "https://*.vercel.app",
        "https://*.pages.dev",
    ],
    allow_origin_regex=r"https://.*\.(vercel|pages)\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Auth"])
app.include_router(backtest.router, prefix=f"{settings.API_V1_PREFIX}/backtest", tags=["Backtest"])
app.include_router(data.router, prefix=f"{settings.API_V1_PREFIX}/data", tags=["Data"])
app.include_router(billing.router, prefix=f"{settings.API_V1_PREFIX}/billing", tags=["Billing"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(share.router, prefix=f"{settings.API_V1_PREFIX}/backtest", tags=["Share"])
app.include_router(share.router, prefix=f"{settings.API_V1_PREFIX}/share", tags=["Share"])
app.include_router(optimization.router, prefix=f"{settings.API_V1_PREFIX}/optimize", tags=["Optimize"])


@app.get("/health")
async def health():
    """Health check for Render and Cron-Job.org keep-alive.

    Render free tier spins down after 15 min of inactivity.
    Cron-Job.org pings this endpoint every 14 minutes to keep the service alive.
    """
    db_status = "ok"
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
