from __future__ import annotations

from typing import Any, Optional

import httpx


class ObserverClient:
    def __init__(self, http_client: httpx.AsyncClient, observer_url: str) -> None:
        self.http_client = http_client
        self.observer_url = observer_url

    async def report_thought(self, payload: dict[str, Any]) -> None:
        await self.http_client.post(f"{self.observer_url}/api/thought", json=payload)

    async def report_activity(self, payload: dict[str, Any]) -> None:
        await self.http_client.post(f"{self.observer_url}/api/activity", json=payload)

    async def send_heartbeat(self, payload: dict[str, Any]) -> None:
        await self.http_client.post(f"{self.observer_url}/api/heartbeat", json=payload)

    async def notify_birth(self, payload: dict[str, Any]) -> httpx.Response:
        response = await self.http_client.post(f"{self.observer_url}/api/birth", json=payload)
        return response

    async def fetch_system_stats(self) -> dict[str, Any]:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/system/stats", timeout=5.0)
            if response.status_code != 200:
                return {}
            data = response.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    async def fetch_messages_count(self) -> Optional[int]:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/messages/count")
            response.raise_for_status()
            data = response.json()
            return int(data.get("count", 0))
        except Exception:
            return None

    async def fetch_blog_post_count(self) -> Optional[int]:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/blog/posts")
            response.raise_for_status()
            data = response.json()
            return int(data.get("count", 0))
        except Exception:
            return None

    async def fetch_votes(self) -> dict[str, Any]:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/votes")
            return response.json()
        except Exception:
            return {}

    async def fetch_messages(self) -> dict[str, Any]:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/messages")
            return response.json()
        except Exception:
            return {}

    async def mark_messages_read(self, message_ids: list[int]) -> None:
        await self.http_client.post(f"{self.observer_url}/api/messages/read", json={"ids": message_ids})

    async def fetch_state(self) -> dict[str, Any]:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/state")
            return response.json()
        except Exception:
            return {}
