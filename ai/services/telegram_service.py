from typing import Any

from ..safety.content_filter import is_content_blocked
from ..telegram_notifier import notifier


class TelegramService:
    async def post_to_channel(
        self,
        content: str,
        identity: dict[str, Any] | None,
        report_activity,
    ) -> str:
        if len(content) > 1000:
            return f"❌ Post too long ({len(content)} chars). Maximum is 1000 characters for readability."

        if len(content) < 10:
            return "❌ Post too short. Write something meaningful!"

        if is_content_blocked(content):
            await report_activity("telegram_blocked", "Blocked by safety filter")
            return "🚫 Content blocked by safety filter."

        await report_activity("posting_telegram", f"Telegram: {content[:50]}...")

        try:
            name = str(identity.get("name", "Unknown")) if identity else "Unknown"
            icon = str(identity.get("icon", "🤖")) if identity else "🤖"

            formatted_content = f"""{icon} *{name}*

{content}

🔗 am-i-alive.muadiv.com.ar"""

            success, message = await notifier.post_to_channel(formatted_content)

            if success:
                await report_activity("telegram_posted", f"Posted: {content[:50]}...")
                return "✅ Posted to Telegram channel! Your message is now public."
            await report_activity("telegram_failed", message)
            return f"❌ Failed to post: {message}"
        except Exception as e:
            error_msg = str(e)[:200]
            await report_activity("telegram_error", error_msg)
            return f"❌ Error posting to Telegram: {error_msg}"
