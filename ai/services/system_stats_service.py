from __future__ import annotations

from typing import Any, Optional

import httpx


class SystemStatsService:
    def __init__(self, http_client: httpx.AsyncClient, observer_url: str) -> None:
        self.http_client = http_client
        self.observer_url = observer_url

    async def fetch_stats(self) -> dict[str, Any]:
        try:
            response = await self.http_client.get(f"{self.observer_url}/api/system/stats", timeout=5.0)
            if response.status_code != 200:
                return {}
            data = response.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def format_temp(temp_value: Optional[Any]) -> str:
        if temp_value in (None, "unknown"):
            return "unknown"
        try:
            return f"{float(temp_value):.1f}°C"
        except (TypeError, ValueError):
            return f"{temp_value}°C"

    @staticmethod
    def format_percent(value: Optional[Any]) -> str:
        if value is None:
            return "unknown"
        try:
            return f"{float(value):.1f}%"
        except (TypeError, ValueError):
            return "unknown"

    @staticmethod
    def format_uptime(seconds: Optional[Any]) -> str:
        if seconds is None:
            return "unknown uptime"
        try:
            seconds_int = int(seconds)
        except (TypeError, ValueError):
            return "unknown uptime"

        if seconds_int < 60:
            return f"{seconds_int}s"
        minutes, rem = divmod(seconds_int, 60)
        if minutes < 60:
            return f"{minutes}m {rem}s"
        hours, rem = divmod(minutes, 60)
        if hours < 24:
            return f"{hours}h {rem}m"
        days, rem = divmod(hours, 24)
        return f"{days}d {rem}h"

    def build_summary(self, stats: dict[str, Any]) -> str:
        if not stats:
            return ""

        temp_text = self.format_temp(stats.get("cpu_temp"))
        cpu_text = self.format_percent(stats.get("cpu_usage"))
        ram_text = self.format_percent(stats.get("ram_usage"))
        disk_text = self.format_percent(stats.get("disk_usage"))
        uptime_text = self.format_uptime(stats.get("uptime_seconds"))
        ram_available = stats.get("ram_available", "unknown")

        return (
            f"My body temperature is {temp_text}, CPU at {cpu_text}, "
            f"RAM at {ram_text} ({ram_available} free), disk at {disk_text}, "
            f"and I've been awake for {uptime_text}."
        )
