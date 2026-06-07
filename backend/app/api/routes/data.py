"""
Data endpoints — ticker validation, CSV preview, symbol search.

GET   /api/v1/data/validate-ticker  — check if a ticker exists
POST  /api/v1/data/preview          — upload CSV, preview first 100 rows
GET   /api/v1/data/search           — search symbols
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response, error_http
from app.models.user import User
from app.api.deps import get_current_user
from app.services.data_service import (
    parse_csv_upload,
    validate_ohlcv,
    search_symbols,
)

router = APIRouter()


@router.get("/validate-ticker")
async def validate_ticker(
    ticker: str = Query(..., min_length=1, max_length=20),
    _current_user: User = Depends(get_current_user),
):
    """
    Validate whether a ticker symbol is recognized by Yahoo Finance.

    Returns:
    - valid: bool
    - name: string (if known)
    - exchange: string (if known)
    - earliest_date: earliest available data
    """
    import re

    ticker = ticker.strip().upper()
    symbol_pattern = r"^[A-Z0-9.\-^=]{1,20}$"
    if not re.match(symbol_pattern, ticker):
        return success_response(
            data={
                "valid": False,
                "name": None,
                "exchange": None,
                "error": "Invalid ticker format",
            }
        )

    # Try Yahoo Finance
    try:
        import yfinance as yf
        import asyncio

        t = yf.Ticker(ticker)
        info = await asyncio.wait_for(
            asyncio.to_thread(lambda: t.info),
            timeout=5.0,
        )

        # Check response quality
        if info is None or info.get("trailingPegRatio") is None and not info.get("shortName"):
            # Try fetching history as a fallback check
            hist = t.history(period="5d")
            if hist.empty:
                return success_response(
                    data={
                        "valid": False,
                        "name": None,
                        "exchange": None,
                        "error": f"Ticker '{ticker}' not found or has no recent data",
                    }
                )

        earliest = None
        try:
            hist_long = t.history(period="max")
            if not hist_long.empty:
                earliest = hist_long.index[0].strftime("%Y-%m-%d")
        except Exception:
            pass

        return success_response(
            data={
                "valid": True,
                "name": info.get("shortName") or info.get("longName") or ticker,
                "exchange": info.get("exchange") or info.get("fullExchangeName"),
                "earliest_date": earliest,
            }
        )
    except asyncio.TimeoutError:
        raise error_http("external.timeout", "Yahoo Finance timed out", status_code=504)
    except Exception as exc:
        raise error_http(
            "external.api_error",
            f"Failed to validate ticker: {exc}",
            status_code=502,
        )


@router.post("/preview")
async def preview_csv(
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_user),
):
    """
    Upload a CSV file for preview.

    Returns:
    - columns: detected column mapping
    - rows: first 100 data rows (as JSON)
    - validation: ValidationResult (errors + warnings)
    - row_count: total rows in file
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise error_http(
            "validation.error",
            "File must be a CSV (.csv extension)",
            status_code=422,
        )

    file_content = await file.read()
    if len(file_content) == 0:
        raise error_http("validation.error", "Uploaded file is empty", status_code=422)
    if len(file_content) > 50 * 1024 * 1024:  # 50 MB limit
        raise error_http(
            "validation.error",
            "File too large. Maximum size is 50 MB.",
            status_code=422,
        )

    try:
        df = parse_csv_upload(file_content)
    except ValueError as e:
        raise error_http("validation.error", str(e), status_code=422)

    validation = validate_ohlcv(df)
    total_rows = len(df)
    preview_rows = df.head(100)

    # Build response
    columns = list(preview_rows.columns)
    rows_data = []
    for idx, row in preview_rows.iterrows():
        row_dict = {"date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)}
        for col in columns:
            val = row[col]
            if hasattr(val, "item"):
                val = float(val)
            elif hasattr(val, "tolist"):
                val = val.tolist()
            row_dict[col] = val
        rows_data.append(row_dict)

    return success_response(
        data={
            "columns": columns,
            "rows": rows_data,
            "row_count": total_rows,
            "validation": {
                "is_valid": validation.is_valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        }
    )


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, max_length=50),
    _current_user: User = Depends(get_current_user),
):
    """
    Search for symbols matching the query string.

    Returns a list of {symbol, name} objects.
    """
    results = await search_symbols(q)
    return success_response(data={"results": results})
