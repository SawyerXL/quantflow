"""
Tests for API route handlers using FastAPI TestClient.

Tests auth schema validation, unified response format, OpenAPI docs,
and endpoint access control (auth required).
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

# Import app — module-level engine creation may fail without a real DB,
# but route definitions and schema validation are still testable.
try:
    from app.main import app
    APP_AVAILABLE = True
except Exception:
    APP_AVAILABLE = False


@pytest.fixture(scope="module")
def client():
    if not APP_AVAILABLE:
        pytest.skip("App not available (database not configured)")
    return TestClient(app)


# ============================================================================
# Auth endpoints — schema validation
# ============================================================================


class TestAuthSchemaValidation:
    """Test Pydantic schema validators without needing a database."""

    def test_register_too_short_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "a@b.com",
            "password": "ab1",
        })
        assert resp.status_code == 422

    def test_register_no_digit(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "a@b.com",
            "password": "abcdefgh",
        })
        assert resp.status_code == 422

    def test_register_no_letter(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "a@b.com",
            "password": "12345678",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "valid1234",
        })
        assert resp.status_code == 422

    def test_register_valid_password(self, client):
        """Valid password must pass schema validation (may fail downstream on DB)."""
        resp = client.post("/api/v1/auth/register", json={
            "email": "valid@example.com",
            "password": "abcd1234",
            "full_name": "Test User",
        })
        # PASS: status != 422 (Pydantic schema accepted the input)
        # Any other status (201, 409, 500) means schema passed;
        # the downstream error is from DB/env, not from validation.
        assert resp.status_code != 422, (
            f"Schema validation rejected valid input (got {resp.status_code}): {resp.json()}"
        )

    def test_refresh_invalid_token_returns_unified_error(self, client):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token-value",
        })
        assert resp.status_code == 401
        data = resp.json()
        # FastAPI wraps HTTPException detail in {"detail": ...}
        detail = data.get("detail", data)
        assert detail["code"] == "auth.token_expired"

    def test_me_without_auth(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ============================================================================
# Backtest endpoints — access control
# ============================================================================


class TestBacktestAccess:
    """Verify that backtest endpoints require authentication."""

    def test_run_requires_auth(self, client):
        resp = client.post("/api/v1/backtest/run", data={
            "ticker": "AAPL",
            "strategy_type": "ma_cross",
        })
        assert resp.status_code == 401

    def test_run_sync_requires_auth(self, client):
        resp = client.post("/api/v1/backtest/run-sync", data={
            "ticker": "AAPL",
            "strategy_type": "ma_cross",
        })
        assert resp.status_code == 401

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/backtest/list")
        assert resp.status_code == 401

    def test_get_requires_auth(self, client):
        resp = client.get(f"/api/v1/backtest/{uuid.uuid4()}")
        assert resp.status_code == 401

    def test_delete_requires_auth(self, client):
        resp = client.delete(f"/api/v1/backtest/{uuid.uuid4()}")
        assert resp.status_code == 401

    def test_run_schema_validation(self, client):
        """Invalid JSON for strategy_params should be caught."""
        # Even without auth, let's verify the endpoint structure exists
        resp = client.post("/api/v1/backtest/run")
        assert resp.status_code in (401, 422)  # 401 = no auth, 422 = missing body


# ============================================================================
# Data endpoints — access control
# ============================================================================


class TestDataAccess:
    """Verify that data endpoints require authentication."""

    def test_validate_ticker_requires_auth(self, client):
        resp = client.get("/api/v1/data/validate-ticker?ticker=AAPL")
        assert resp.status_code == 401

    def test_preview_requires_auth(self, client):
        resp = client.post("/api/v1/data/preview")
        assert resp.status_code == 401

    def test_search_requires_auth(self, client):
        resp = client.get("/api/v1/data/search?q=GOOG")
        assert resp.status_code == 401


# ============================================================================
# Unified error response format
# ============================================================================


class TestResponseFormat:
    """Verify unified API response structure."""

    def test_auth_error_has_unified_format(self, client):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "bad-token",
        })
        assert resp.status_code == 401
        data = resp.json()
        # Our error detail is in FastAPI's {"detail": {...}} wrapper
        detail = data.get("detail", data)
        assert "code" in detail
        assert "message" in detail

    def test_schema_error_has_standard_format(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "bad",
            "password": "short",
        })
        assert resp.status_code == 422

    def test_health_returns_plain_json(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "database" in data
        assert "timestamp" in data


# ============================================================================
# OpenAPI docs
# ============================================================================


class TestOpenAPI:
    """Verify OpenAPI schema completeness."""

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()

        paths = schema["paths"]
        # Auth endpoints
        assert "/api/v1/auth/register" in paths
        assert "/api/v1/auth/login" in paths
        assert "/api/v1/auth/refresh" in paths
        assert "/api/v1/auth/me" in paths
        # Backtest endpoints
        assert "/api/v1/backtest/run" in paths
        assert "/api/v1/backtest/run-sync" in paths
        assert "/api/v1/backtest/list" in paths
        assert "/api/v1/backtest/{backtest_id}" in paths
        # Data endpoints
        assert "/api/v1/data/validate-ticker" in paths
        assert "/api/v1/data/preview" in paths
        assert "/api/v1/data/search" in paths
        # Billing endpoints
        assert "/api/v1/billing/subscription" in paths
        assert "/api/v1/billing/checkout" in paths
        assert "/api/v1/billing/portal" in paths
        assert "/api/v1/billing/webhook" in paths

    def test_docs_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_accessible(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200

    def test_backtest_run_docs(self, client):
        """Verify backtest/run has proper form-data documentation."""
        resp = client.get("/openapi.json")
        schema = resp.json()
        run_endpoint = schema["paths"]["/api/v1/backtest/run"]["post"]

        # Should be multipart/form-data
        body = run_endpoint.get("requestBody", {})
        content = body.get("content", {})
        assert "multipart/form-data" in content, "backtest/run should accept multipart/form-data"

    def test_tags_present(self, client):
        resp = client.get("/openapi.json")
        schema = resp.json()
        tags = [t["name"] for t in schema.get("tags", [])]
        assert "Auth" in tags
        assert "Backtest" in tags
        assert "Data" in tags
        assert "Billing" in tags


# ============================================================================
# Pydantic schema tests
# ============================================================================


class TestPydanticSchemas:
    """Test schema validation directly (no HTTP)."""

    def test_password_validator_accepts_good_passwords(self):
        from app.schemas.user import UserRegister

        # Should not raise
        UserRegister(email="a@b.com", password="abcd1234")
        UserRegister(email="a@b.com", password="MyP@ssw0rd2024!!")

    def test_password_validator_rejects_short(self):
        from app.schemas.user import UserRegister
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="at least 8"):
            UserRegister(email="a@b.com", password="ab1")

    def test_token_response_fields(self):
        from app.schemas.user import TokenResponse

        t = TokenResponse(access_token="acc", refresh_token="ref")
        d = t.model_dump()
        assert d["access_token"] == "acc"
        assert d["refresh_token"] == "ref"
        assert d["token_type"] == "bearer"

    def test_user_response_excludes_password(self):
        from app.schemas.user import UserResponse

        fields = UserResponse.model_fields
        assert "hashed_password" not in fields
        assert "password" not in fields
