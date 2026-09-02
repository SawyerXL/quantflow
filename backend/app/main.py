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
from app.api.routes import auth, backtest, data, billing, dashboard, share, optimization, demo

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
        # 2026-09-02 新增: 迁移链完整性检查——create_all只建新表, 不补已存在
        # 表的缺列(migrations/0002的share_slug等)。生产库若由create_all创建
        # 且从未跑过alembic, share路由会静默500。此处把缺口变成启动期可见
        # 的明确错误, 而非运行期无头故障。
        try:
            from sqlalchemy import text
            res = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='backtests' AND column_name='share_slug'"
            ))
            if res.first() is None:
                logger.error(
                    "DB schema incomplete: backtests.share_slug missing. "
                    "Run: alembic stamp 20260606_0001 && alembic upgrade head "
                    "(migrations/versions/) — 只ALTER不重建。"
                )
        except Exception:
            pass  # DB未就绪时健康检查会暴露, 不阻断启动
    # Pre-compute demos in background (non-blocking)
    import asyncio as _asyncio
    from app.services.demo_service import precompute_demos
    _asyncio.create_task(precompute_demos())
    yield
    await engine.dispose()


# ── App ──────────────────────────────────────────────────────────────────────


app = FastAPI(
    title=settings.APP_NAME,
    description="Quantitative backtesting SaaS platform — build, test, "
    "and deploy algorithmic trading strategies.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
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
            # 2026-09-02 安全修复: 不把异常类型/消息回传客户端(SQLAlchemy/asyncpg
            # 报错可带SQL语句/DSN片段, 放大泄露面); 细节只进服务端日志/Sentry
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "server.error",
                        "message": "Internal server error",
                    },
                },
            )
        return response


app.add_middleware(UnifiedErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    # 2026-09-02 安全修复: ① 通配字符串"https://*.vercel.app"在starlette是
    # 字面匹配、从未生效(死配置); ② allow_credentials=True + 任意*.pages.dev
    # 正则 = 免费注册的Cloudflare Pages域成为信任源, 一旦改cookie认证即全量
    # 账号接管。当前前端用localStorage+Bearer(跨源JS读不到token), 不依赖
    # credentials; 去掉credentials+保留显式origin列表。
    allow_origins=[
        "http://localhost:3000",
        "https://quantflow-two.vercel.app",
        "https://quantflow.pages.dev",
    ],
    allow_credentials=False,
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
app.include_router(demo.router, prefix=f"{settings.API_V1_PREFIX}/demo", tags=["Demo"])


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
