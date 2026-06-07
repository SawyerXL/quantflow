"""
Unified API response helpers.

Every endpoint returns:
    Success: {"success": true, "data": {...}}
    Error:   {"success": false, "error": {"code": "...", "message": "...", "details": null}}
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

# ── Error codes ──────────────────────────────────────────────────────────────

ERROR_CODES = {
    "auth.invalid_credentials": 401,
    "auth.token_expired": 401,
    "auth.token_invalid": 401,
    "auth.insufficient_permissions": 403,
    "rate_limit.exceeded": 429,
    "validation.error": 422,
    "resource.not_found": 404,
    "resource.conflict": 409,
    "backtest.limit_reached": 403,
    "backtest.data_insufficient": 400,
    "backtest.invalid_params": 400,
    "external.api_error": 502,
    "external.timeout": 504,
    "server.error": 500,
}


def success_response(data: Any = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({"success": True, "data": data}),
    )


def error_response(
    code: str,
    message: str,
    details: Any = None,
    status_code: int | None = None,
) -> JSONResponse:
    status = status_code or ERROR_CODES.get(code, 500)
    return JSONResponse(
        status_code=status,
        content=jsonable_encoder({
            "success": False,
            "error": {"code": code, "message": message, "details": details},
        }),
    )


def error_http(
    code: str,
    message: str,
    details: Any = None,
    status_code: int | None = None,
):
    """Raise an HTTPException with the unified error body structure."""
    status = status_code or ERROR_CODES.get(code, 500)
    raise HTTPException(
        status_code=status,
        detail={"code": code, "message": message, "details": details},
    )
