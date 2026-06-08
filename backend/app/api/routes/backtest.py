"""
Backtest endpoints — run, list, get, delete.

POST /api/v1/backtest/run       — async backtest (file upload or ticker)
POST /api/v1/backtest/run-sync  — synchronous backtest (returns results directly)
GET  /api/v1/backtest/list      — paginated history
GET  /api/v1/backtest/{id}      — single result
DELETE /api/v1/backtest/{id}    — delete result
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response, error_http
from app.models.user import User
from app.models.backtest import BacktestResult
from app.models.enums import BacktestStatus, DataSource, enum_value
from app.schemas.backtest import BacktestResponse, BacktestListResponse
from app.api.deps import get_current_user, check_rate_limit
from app.services.backtest_engine import (
    BacktestInput,
    run_backtest,
    run_backtest_async,
)
from app.services.data_service import (
    parse_csv_upload,
    validate_ohlcv,
    preprocess_data,
    get_yahoo_data,
)

router = APIRouter()


# ── Shared helpers ───────────────────────────────────────────────────────────


async def _check_daily_limit(user: User, db: AsyncSession) -> None:
    """Enforce daily backtest limit for free-tier users."""
    if enum_value(user.plan) == "free":
        now = datetime.now(timezone.utc)
        # Reset count if the day has changed
        if user.backtest_count_reset_at is None or user.backtest_count_reset_at.date() < now.date():
            user.backtest_count_today = 0
            user.backtest_count_reset_at = now
            await db.flush()

        from app.core.config import get_settings
        settings = get_settings()

        if user.backtest_count_today >= settings.FREE_USER_DAILY_BACKTESTS:
            raise error_http(
                "backtest.limit_reached",
                f"Daily backtest limit ({settings.FREE_USER_DAILY_BACKTESTS}) reached. "
                f"Upgrade to Pro for unlimited backtests.",
                status_code=403,
            )

        user.backtest_count_today += 1
        user.backtest_count_reset_at = now
        await db.flush()


# ── POST /run ────────────────────────────────────────────────────────────────


@router.post("/run", status_code=201)
async def create_backtest(
    # --- file upload branch ---
    file: Optional[UploadFile] = File(None),
    # --- ticker branch ---
    ticker: Optional[str] = Form(None),
    # --- common ---
    strategy_type: str = Form(...),
    strategy_params: str = Form("{}"),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    initial_capital: float = Form(10000.0),
    name: Optional[str] = Form(None),
    # --- deps ---
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(check_rate_limit),
):
    """
    Run an asynchronous backtest.

    Provide either a CSV `file` OR a `ticker` symbol (not both).
    The backtest runs in the background; poll GET /{id} for results.
    """
    # Validate: file XOR ticker
    if file and ticker:
        raise error_http(
            "validation.error",
            "Provide either a CSV file or a ticker symbol, not both.",
            status_code=422,
        )
    if not file and not ticker:
        raise error_http(
            "validation.error",
            "Provide a CSV file or a ticker symbol.",
            status_code=422,
        )

    # Parse strategy params
    try:
        params = json.loads(strategy_params)
    except json.JSONDecodeError:
        raise error_http(
            "validation.error",
            "strategy_params must be valid JSON",
            status_code=422,
        )

    if strategy_type not in ("ma_cross", "rsi", "bollinger", "macd"):
        raise error_http(
            "validation.error",
            f"Unknown strategy_type '{strategy_type}'. Supported: ma_cross, rsi, bollinger, macd",
            status_code=422,
        )

    # Check daily limit for free users
    await _check_daily_limit(current_user, db)

    # Determine data source
    if file:
        data_source = DataSource.upload
        file_content = await file.read()
        try:
            ohlcv_data = parse_csv_upload(file_content)
        except ValueError as e:
            raise error_http("validation.error", str(e), status_code=422)
    else:
        data_source = DataSource.yahoo
        ohlcv_data = None  # Will be fetched by the engine

    # Build backtest record
    name = name or f"{strategy_type.upper()} on {ticker or file.filename or 'unknown'}"
    # Use today's date range as fallback
    s_date = start_date or "2020-01-01"
    e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    import dateutil.parser

    backtest = BacktestResult(
        user_id=current_user.id,
        name=name,
        ticker=ticker or (file.filename if file else "unknown"),
        data_source=enum_value(data_source),
        start_date=dateutil.parser.parse(str(s_date)).date(),
        end_date=dateutil.parser.parse(str(e_date)).date(),
        initial_capital=initial_capital,
        status=BacktestStatus.pending,
    )
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)

    # Spawn background task (async — immediate return)
    # In production this goes to Celery; for now we use asyncio.create_task
    import asyncio

    async def _run_and_save():
        from app.core.database import async_session_factory

        async with async_session_factory() as bg_db:
            result = await bg_db.get(BacktestResult, backtest.id)
            if result is None:
                return
            result.status = BacktestStatus.running
            await bg_db.commit()

            try:
                if ohlcv_data is None and ticker:
                    ohlcv_data = await get_yahoo_data(ticker, s_date, e_date)

                bt_input = BacktestInput(
                    ohlcv_data=ohlcv_data,
                    strategy_type=strategy_type,
                    strategy_params=params,
                    initial_capital=initial_capital,
                    start_date=str(start_date) if start_date else None,
                    end_date=str(end_date) if end_date else None,
                )
                output = await run_backtest_async(bt_input)

                result.status = BacktestStatus.completed
                result.total_return = output.total_return
                result.annual_return = output.annual_return
                result.sharpe_ratio = output.sharpe_ratio
                result.max_drawdown = output.max_drawdown
                result.win_rate = output.win_rate
                result.total_trades = output.total_trades
                result.profit_factor = output.profit_factor
                result.result_data = {
                    "equity_curve": output.equity_curve,
                    "drawdown_curve": output.drawdown_curve,
                    "trades": output.trades,
                }
                result.completed_at = datetime.now(timezone.utc)
            except Exception as exc:
                result.status = BacktestStatus.failed
                result.error_message = str(exc)

            await bg_db.commit()

    asyncio.create_task(_run_and_save())

    return success_response(
        data={
            "id": str(backtest.id),
            "name": backtest.name,
            "status": enum_value(backtest.status),
        },
        status_code=201,
    )


# ── POST /run-sync ───────────────────────────────────────────────────────────


@router.post("/run-sync", status_code=201)
async def create_backtest_sync(
    file: Optional[UploadFile] = File(None),
    ticker: Optional[str] = Form(None),
    strategy_type: str = Form(...),
    strategy_params: str = Form("{}"),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    initial_capital: float = Form(10000.0),
    name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(check_rate_limit),
):
    """
    Run a synchronous backtest. Returns full results immediately.

    This is intended for testing and small backtests.
    Production backtests should use POST /run for async execution.
    """
    if file and ticker:
        raise error_http("validation.error", "Provide either a CSV file or a ticker, not both.", status_code=422)
    if not file and not ticker:
        raise error_http("validation.error", "Provide a CSV file or a ticker.", status_code=422)

    try:
        params = json.loads(strategy_params)
    except json.JSONDecodeError:
        raise error_http("validation.error", "strategy_params must be valid JSON", status_code=422)

    if strategy_type not in ("ma_cross", "rsi", "bollinger", "macd"):
        raise error_http(
            "validation.error",
            f"Unknown strategy_type '{strategy_type}'. Supported: ma_cross, rsi, bollinger, macd",
            status_code=422,
        )

    await _check_daily_limit(current_user, db)

    # Load data
    if file:
        file_content = await file.read()
        try:
            ohlcv_data = parse_csv_upload(file_content)
        except ValueError as e:
            raise error_http("validation.error", str(e), status_code=422)
        ticker_name = file.filename or "upload"
    else:
        s_date = start_date or "2020-01-01"
        e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ohlcv_data = await get_yahoo_data(ticker, s_date, e_date)
        ticker_name = ticker

    name = name or f"{strategy_type.upper()} on {ticker_name}"

    # Validate and preprocess
    validation = validate_ohlcv(ohlcv_data)
    if not validation.is_valid:
        raise error_http(
            "validation.error",
            "Data validation failed",
            details={"errors": validation.errors, "warnings": validation.warnings},
            status_code=422,
        )

    ohlcv_data = preprocess_data(ohlcv_data, start_date, end_date)

    # Run backtest
    bt_input = BacktestInput(
        ohlcv_data=ohlcv_data,
        strategy_type=strategy_type,
        strategy_params=params,
        initial_capital=initial_capital,
        start_date=start_date,
        end_date=end_date,
    )
    output = run_backtest(bt_input)

    import dateutil.parser

    s_date = start_date or "2020-01-01"
    e_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Save to database
    backtest = BacktestResult(
        user_id=current_user.id,
        name=name,
        ticker=ticker_name,
        data_source=DataSource.upload.value if file else DataSource.yahoo.value,
        start_date=dateutil.parser.parse(str(s_date)).date(),
        end_date=dateutil.parser.parse(str(e_date)).date(),
        initial_capital=initial_capital,
        status=BacktestStatus.completed,
        total_return=output.total_return,
        annual_return=output.annual_return,
        sharpe_ratio=output.sharpe_ratio,
        max_drawdown=output.max_drawdown,
        win_rate=output.win_rate,
        total_trades=output.total_trades,
        profit_factor=output.profit_factor,
        result_data={
            "equity_curve": output.equity_curve,
            "drawdown_curve": output.drawdown_curve,
            "trades": output.trades,
        },
        completed_at=datetime.now(timezone.utc),
    )
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)

    return success_response(
        data=BacktestResponse.model_validate(backtest).model_dump(),
        status_code=201,
    )


# ── GET /list ────────────────────────────────────────────────────────────────


@router.get("/list")
async def list_backtests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the current user's backtests, newest first.

    Query params:
    - page: Page number (1-indexed).
    - limit: Items per page (1-100).
    - status: Optional filter — pending, running, completed, failed.
    """
    base = select(BacktestResult).where(BacktestResult.user_id == current_user.id)
    count_base = select(func.count()).select_from(BacktestResult).where(
        BacktestResult.user_id == current_user.id
    )

    if status:
        base = base.where(BacktestResult.status == status)
        count_base = count_base.where(BacktestResult.status == status)

    total = await db.scalar(count_base)
    offset = (page - 1) * limit

    stmt = base.order_by(BacktestResult.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return success_response(
        data={
            "items": [BacktestListResponse.model_validate(item).model_dump() for item in items],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, (total + limit - 1) // limit) if total else 1,
        },
    )


# ── GET /{id} ────────────────────────────────────────────────────────────────


@router.get("/{backtest_id}")
async def get_backtest(
    backtest_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single backtest result by ID.
    Returns full results including equity curve and trades if completed.
    """
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.id == backtest_id,
            BacktestResult.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise error_http(
            "resource.not_found",
            "Backtest not found",
            status_code=404,
        )

    return success_response(
        data=BacktestResponse.model_validate(backtest).model_dump(),
    )


# ── DELETE /{id} ─────────────────────────────────────────────────────────────


@router.delete("/{backtest_id}", status_code=200)
async def delete_backtest(
    backtest_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a backtest record. Only the owner can delete.
    """
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.id == backtest_id,
            BacktestResult.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise error_http("resource.not_found", "Backtest not found", status_code=404)

    await db.delete(backtest)
    await db.commit()

    return success_response(data={"id": str(backtest_id), "deleted": True})
