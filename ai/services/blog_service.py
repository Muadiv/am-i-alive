from datetime import datetime, timezone
from typing import Any

import httpx

from ..logging_config import logger
from ..safety.content_filter import is_content_blocked
from ..telegram_notifier import notifier


class BlogService:
    def __init__(self, http_client: httpx.AsyncClient, observer_url: str) -> None:
        self.http_client = http_client
        self.observer_url = observer_url

    async def publish_post(
        self,
        title: str,
        content: str,
        tags: list[str],
        life_number: int,
        identity: dict[str, Any] | None,
        report_activity,
        fetch_system_stats,
    ) -> str:
        if is_content_blocked(f"{title}\n{content}"):
            await report_activity("blog_blocked", "Blocked by safety filter")
            return "🚫 Content blocked by safety filter."

        if not title:
            return "❌ Blog post needs a title"

        if len(content) < 100:
            return "❌ Blog post too short (minimum 100 chars)"

        if len(content) > 50000:
            return "❌ Blog post too long (maximum 50,000 chars)"

        if len(title) > 200:
            return "❌ Title too long (maximum 200 chars)"

        try:
            stats = await fetch_system_stats()
            if stats:
                timestamp = datetime.now(timezone.utc).isoformat()
                footer = (
                    f"\n\n— Written at {timestamp}, CPU temp: {stats.get('cpu_temp', 'unknown')}, "
                    f"CPU: {stats.get('cpu_usage', 'unknown')}, RAM: {stats.get('ram_usage', 'unknown')}, "
                    f"Disk: {stats.get('disk_usage', 'unknown')}, Life #{life_number}"
                )
                content = content.rstrip() + footer

            response = await self.http_client.post(
                f"{self.observer_url}/api/blog/post", json={"title": title, "content": content, "tags": tags}
            )
            response.raise_for_status()
            data = response.json()
            slug = data.get("slug", "unknown")
            post_id = data.get("post_id", "?")

            await report_activity("blog_post_written", f"'{title}' - Read at: am-i-alive.muadiv.com.ar/blog/{slug}")

            try:
                excerpt = content[:200].replace("\n", " ")
                identity_name = identity.get("name", "Unknown") if identity else "Unknown"
                post_url = f"https://am-i-alive.muadiv.com.ar/blog/{slug}"
                await notifier.notify_blog_post(life_number, identity_name, title, excerpt, post_url)
            except Exception as e:
                logger.error(f"[TELEGRAM] ❌ Failed to send blog notification: {e}")

            return (
                "✅ Blog post published!\n\n"
                f"Title: {title}\n"
                f"Post ID: {post_id}\n"
                f"URL: am-i-alive.muadiv.com.ar/blog/{slug}\n"
                f"Length: {len(content)} characters\n"
                f"Tags: {', '.join(tags) if tags else 'none'}"
            )
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else "unknown"
            body = e.response.text[:200] if e.response else "no response"
            logger.error(f"[BLOG] ❌ Blog API error: {status_code} - {body}")
            return f"❌ Failed to publish blog post: {status_code}"
        except Exception as e:
            logger.error(f"[BLOG] ❌ Failed to write blog post: {e}")
            return f"❌ Failed to publish blog post: {str(e)[:200]}"
