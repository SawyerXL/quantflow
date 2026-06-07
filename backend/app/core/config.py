from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──
    APP_NAME: str = "QuantFlow"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ── Database (Supabase pooler) ──
    DATABASE_URL: str = "postgresql+asyncpg://quantflow:quantflow@localhost:5432/quantflow"
    DATABASE_URL_SYNC: str = "postgresql://quantflow:quantflow@localhost:5432/quantflow"
    DB_POOL_SIZE: int = 3   # Supabase free tier — keep low
    DB_MAX_OVERFLOW: int = 0

    # ── Redis (Upstash HTTP REST API) ──
    REDIS_URL: str = ""
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    # ── Auth ──
    JWT_SECRET: str = "change-me-to-a-random-secret-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Rate limiting ──
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_FREE_USER: int = 100
    RATE_LIMIT_PRO_USER: int = 0
    RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # ── Backtest limits ──
    FREE_USER_DAILY_BACKTESTS: int = 5

    # ── Stripe ──
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_MONTHLY_PRICE_ID: str = ""
    STRIPE_PRO_YEARLY_PRICE_ID: str = ""
    STRIPE_QUANT_MONTHLY_PRICE_ID: str = ""
    STRIPE_QUANT_YEARLY_PRICE_ID: str = ""

    # ── Cloudflare R2 (S3-compatible storage) ──
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "quantflow-uploads"

    # ── Resend email ──
    RESEND_API_KEY: str = ""

    # ── Sentry error monitoring ──
    SENTRY_DSN: str = ""

    # ── Data providers ──
    ALPHA_VANTAGE_API_KEY: str = ""
    POLYGON_API_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
