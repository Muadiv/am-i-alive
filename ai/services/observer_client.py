from __future__ import annotations

from typing import Any, Optional

import logging

import httpx

from .interfaces import ObserverClientProtocol


logger = logging.getLogger(__name__)


class ObserverClient(ObserverClientProtocol):
    def __init__(self, http_client: httpx.AsyncClient, observer_url: str) -> None:
        self.http_client = http_client
        self.observer_url = observer_url
        self.timeout = 5.0

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.observer_url}{path}"
        if hasattr(self.http_client, "request"):
            return await self.http_client.request(method, url, timeout=self.timeout, **kwargs)
        if method.upper() == "GET" and hasattr(self.http_client, "get"):
            return await self.http_client.get(url, timeout=self.timeout, **kwargs)
        if method.upper() == "POST" and hasattr(self.http_client, "post"):
            return await self.http_client.post(url, timeout=self.timeout, **kwargs)
        raise AttributeError("http_client does not support request")

    async def report_thought(self, payload: dict[str, Any]) -> None:
        try:
            response = await self._request("POST", "/api/thought", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to report thought: {exc}")

    async def report_activity(self, payload: dict[str, Any]) -> None:
        try:
            response = await self._request("POST", "/api/activity", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to report activity: {exc}")

    async def send_heartbeat(self, payload: dict[str, Any]) -> None:
        try:
            response = await self._request("POST", "/api/heartbeat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to send heartbeat: {exc}")

    async def notify_birth(self, payload: dict[str, Any]) -> httpx.Response:
        response = await self._request("POST", "/api/birth", json=payload)
        response.raise_for_status()
        return response

    async def fetch_system_stats(self) -> dict[str, Any]:
        try:
            response = await self._request("GET", "/api/system/stats")
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to fetch system stats: {exc}")
            return {}

    async def fetch_messages_count(self) -> Optional[int]:
        try:
            response = await self._request("GET", "/api/messages/count")
            response.raise_for_status()
            data = response.json()
            return int(data.get("count", 0))
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to fetch messages count: {exc}")
            return None

    async def fetch_blog_post_count(self) -> Optional[int]:
        try:
            response = await self._request("GET", "/api/blog/posts")
            response.raise_for_status()
            data = response.json()
            return int(data.get("count", 0))
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to fetch blog post count: {exc}")
            return None

    async def fetch_votes(self) -> dict[str, Any]:
        try:
            response = await self._request("GET", "/api/votes")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to fetch votes: {exc}")
            return {}

    async def fetch_messages(self) -> dict[str, Any]:
        try:
            response = await self._request("GET", "/api/messages")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to fetch messages: {exc}")
            return {}

    async def mark_messages_read(self, message_ids: list[int]) -> None:
        if not message_ids:
            return
        try:
            response = await self._request("POST", "/api/messages/read", json={"ids": message_ids})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to mark messages read: {exc}")

    async def fetch_state(self) -> dict[str, Any]:
        try:
            response = await self._request("GET", "/api/state")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning(f"[OBSERVER] ⚠️ Failed to fetch state: {exc}")
            return {}
