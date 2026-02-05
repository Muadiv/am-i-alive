from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any

import httpx

MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"


@dataclass
class MoltbookRateLimiter:
    last_post_at: float = 0.0
    last_comment_at: float = 0.0
    daily_comment_count: int = 0
    daily_comment_day: str | None = None

    def _reset_daily_if_needed(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if self.daily_comment_day != today:
            self.daily_comment_day = today
            self.daily_comment_count = 0

    def can_post(self, cooldown_seconds: int = 1800) -> tuple[bool, str]:
        elapsed = time.time() - self.last_post_at
        if elapsed < cooldown_seconds:
            remaining = int(cooldown_seconds - elapsed)
            return False, f"Post cooldown active ({remaining}s remaining)."
        return True, "ok"

    def can_comment(self, cooldown_seconds: int = 20, daily_limit: int = 50) -> tuple[bool, str]:
        self._reset_daily_if_needed()
        if self.daily_comment_count >= daily_limit:
            return False, "Daily comment limit reached."
        elapsed = time.time() - self.last_comment_at
        if elapsed < cooldown_seconds:
            remaining = int(cooldown_seconds - elapsed)
            return False, f"Comment cooldown active ({remaining}s remaining)."
        return True, "ok"

    def mark_post(self) -> None:
        self.last_post_at = time.time()

    def mark_comment(self) -> None:
        self._reset_daily_if_needed()
        self.last_comment_at = time.time()
        self.daily_comment_count += 1


class MoltbookClient:
    def __init__(self, api_key: str, http_client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.http_client = http_client
        self.rate_limiter = MoltbookRateLimiter()

    def _build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{MOLTBOOK_BASE_URL}{path}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = self._build_url(path)
        if not url.startswith(MOLTBOOK_BASE_URL):
            raise ValueError("Moltbook URL must use https://www.moltbook.com/api/v1")
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())
        return await self.http_client.request(method, url, headers=headers, **kwargs)

    async def get_status(self) -> dict[str, Any]:
        response = await self.request("GET", "/agents/status")
        response.raise_for_status()
        return response.json()

    async def get_feed(self, sort: str = "new", limit: int = 10) -> dict[str, Any]:
        response = await self.request(
            "GET",
            "/posts",
            params={"sort": sort, "limit": limit},
        )
        response.raise_for_status()
        return response.json()

    async def create_post(self, submolt: str, title: str, content: str, url: str | None = None) -> dict[str, Any]:
        allowed, reason = self.rate_limiter.can_post()
        if not allowed:
            return {"success": False, "error": reason}
        payload: dict[str, Any] = {"submolt": submolt, "title": title, "content": content}
        if url:
            payload["url"] = url
        response = await self.request("POST", "/posts", json=payload)
        if response.status_code == 429:
            retry_after = self._get_retry_after_seconds(response.json(), minutes_key="retry_after_minutes")
            self._mark_post_retry(retry_after)
            return {"success": False, "error": "Rate limited", "retry_after_seconds": retry_after}
        response.raise_for_status()
        self.rate_limiter.mark_post()
        return response.json()

    async def create_comment(self, post_id: str, content: str, parent_id: str | None = None) -> dict[str, Any]:
        allowed, reason = self.rate_limiter.can_comment()
        if not allowed:
            return {"success": False, "error": reason}
        payload: dict[str, Any] = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        response = await self.request("POST", f"/posts/{post_id}/comments", json=payload)
        if response.status_code == 429:
            retry_after = self._get_retry_after_seconds(response.json(), seconds_key="retry_after_seconds")
            self._mark_comment_retry(retry_after)
            return {"success": False, "error": "Rate limited", "retry_after_seconds": retry_after}
        response.raise_for_status()
        self.rate_limiter.mark_comment()
        return response.json()

    def _get_retry_after_seconds(
        self,
        payload: dict[str, Any],
        minutes_key: str | None = None,
        seconds_key: str | None = None,
    ) -> int:
        if minutes_key and minutes_key in payload:
            try:
                return int(float(payload[minutes_key]) * 60)
            except (TypeError, ValueError):
                return 1800
        if seconds_key and seconds_key in payload:
            try:
                return int(payload[seconds_key])
            except (TypeError, ValueError):
                return 20
        return 1800 if minutes_key else 20

    def _mark_post_retry(self, retry_after_seconds: int) -> None:
        cooldown = 1800
        elapsed = max(0, cooldown - retry_after_seconds)
        self.rate_limiter.last_post_at = time.time() - elapsed

    def _mark_comment_retry(self, retry_after_seconds: int) -> None:
        cooldown = 20
        elapsed = max(0, cooldown - retry_after_seconds)
        self.rate_limiter.last_comment_at = time.time() - elapsed
