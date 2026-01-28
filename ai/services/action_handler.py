from __future__ import annotations

import re
from typing import Any, Callable

import httpx

from .blog_service import BlogService
from .message_service import MessageService
from .telegram_service import TelegramService


class ActionHandler:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        observer_url: str,
        observer_client,
        get_identity: Callable[[], dict[str, Any] | None],
        get_life_number: Callable[[], int],
        report_activity,
        fetch_system_stats,
    ) -> None:
        self.http_client = http_client
        self.observer_url = observer_url
        self.observer_client = observer_client
        self.get_identity = get_identity
        self.get_life_number = get_life_number
        self.report_activity = report_activity
        self.fetch_system_stats = fetch_system_stats

    async def post_to_telegram(self, content: str) -> str:
        service = TelegramService()
        identity = self.get_identity()
        return await service.post_to_channel(content, identity, self.report_activity)

    async def write_blog_post(self, title: str, content: str, tags: list[str] | None = None) -> str:
        if tags is None:
            tags = []

        if not title:
            heading_match = re.match(r"^\s*#{1,3}\s+(.+)", content)
            if heading_match:
                title = heading_match.group(1).strip()
                content = re.sub(r"^\s*#{1,3}\s+.+\n?", "", content, count=1).lstrip()
            else:
                first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
                title = first_line[:120] if first_line else ""

        service = BlogService(self.http_client, self.observer_url)
        return await service.publish_post(
            title=title,
            content=content,
            tags=tags,
            life_number=self.get_life_number(),
            identity=self.get_identity(),
            report_activity=self.report_activity,
            fetch_system_stats=self.fetch_system_stats,
        )

    async def check_votes(self) -> str:
        service = MessageService(self.observer_client)
        return await service.check_votes()

    async def read_messages(self) -> str:
        service = MessageService(self.observer_client)
        return await service.read_messages(self.report_activity)

    async def check_state(self) -> str:
        service = MessageService(self.observer_client)
        return await service.check_state()
