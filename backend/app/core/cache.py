"""
Upstash Redis HTTP cache client.

Upstash free tier: 10,000 commands/day.
Uses HTTPS REST API — no persistent TCP connection needed,
compatible with Render free tier (no raw Redis port access).

Strategy:
- Cache only successful ticker data (TTL 24h)
- Never cache errors
- Stop caching at 8,000 commands/day (keep 20% margin)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UpstashRedis:
    """HTTP client for Upstash Redis REST API.

    Usage:
        cache = UpstashRedis()
        await cache.get("ticker:aaple:2020-01:2020-12")
        await cache.set("key", "value", ttl=86400)
    """

    def __init__(self):
        self.url: str = (settings.UPSTASH_REDIS_REST_URL or "").rstrip("/")
        self.token: str = settings.UPSTASH_REDIS_REST_TOKEN or ""
        self._command_count: int = 0
        self._reset_at: datetime = datetime.now(timezone.utc)
        self._max_commands: int = 8000  # 20% margin below 10k limit
        self._enabled: bool = bool(self.url and self.token)

    @property
    def enabled(self) -> bool:
        return self._enabled and self._commands_remaining > 0

    @property
    def _commands_remaining(self) -> int:
        now = datetime.now(timezone.utc)
        if now.date() > self._reset_at.date():
            self._command_count = 0
            self._reset_at = now
        return self._max_commands - self._command_count

    def _track_command(self):
        self._command_count += 1

    def _make_url(self, path: str) -> str:
        return f"{self.url}/{path}"

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    async def get(self, key: str) -> str | None:
        """GET a key. Returns the string value or None."""
        if not self.enabled:
            return None
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._make_url(f"get/{key}"),
                    headers=self._headers,
                    timeout=5.0,
                )
                self._track_command()
                result = resp.json()
                return result.get("result")
        except Exception as exc:
            logger.debug("Upstash GET error: %s", exc)
            return None

    async def set(self, key: str, value: str, ttl: int = 86400) -> bool:
        """SET a key with TTL in seconds. Returns True on success."""
        if not self.enabled:
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._make_url(f"set/{key}/{value}/ex/{ttl}"),
                    headers=self._headers,
                    timeout=5.0,
                )
                self._track_command()
                return resp.json().get("result") == "OK"
        except Exception as exc:
            logger.debug("Upstash SET error: %s", exc)
            return False

    async def delete(self, key: str) -> bool:
        """DEL a key. Returns True if deleted."""
        if not self.enabled:
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._make_url(f"del/{key}"),
                    headers=self._headers,
                    timeout=5.0,
                )
                self._track_command()
                return resp.json().get("result") == 1
        except Exception as exc:
            logger.debug("Upstash DEL error: %s", exc)
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self.enabled:
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._make_url(f"exists/{key}"),
                    headers=self._headers,
                    timeout=5.0,
                )
                self._track_command()
                return resp.json().get("result") == 1
        except Exception:
            return False

    def stats(self) -> dict:
        """Return usage stats for monitoring."""
        return {
            "commands_used_today": self._command_count,
            "commands_remaining": self._commands_remaining,
            "max_commands": self._max_commands,
            "enabled": self.enabled,
        }


# Global singleton
redis_cache = UpstashRedis()
