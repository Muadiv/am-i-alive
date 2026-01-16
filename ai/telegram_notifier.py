"""
Telegram Notifier for Am I Alive?

Sends activity summaries to the creator's Telegram and public channel.
The public channel is how the AI communicates with the outside world.
"""

import os
import requests
from typing import Optional
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Private chat with creator
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # Public channel for AI posts
OBSERVER_URL = os.getenv("OBSERVER_URL", "http://127.0.0.1")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable must be set")
if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable must be set")
# TELEGRAM_CHANNEL_ID is optional - AI can still function without public channel


def get_internal_headers() -> dict:
    """Headers for Observer internal endpoints."""
    if INTERNAL_API_KEY:
        return {"X-Internal-Key": INTERNAL_API_KEY}
    return {}


class TelegramNotifier:
    """Sends notifications to Telegram (private + public channel)."""

    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID,
                 channel_id: str = TELEGRAM_CHANNEL_ID):
        self.bot_token = bot_token
        self.chat_id = chat_id  # Private chat with creator
        self.channel_id = channel_id  # Public channel (optional)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._last_channel_post = None  # Rate limiting for channel posts

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a text message to private Telegram chat."""
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[TELEGRAM] ❌ Failed to send message: {e}")
            return False

    def post_to_channel(self, text: str, parse_mode: str = "Markdown") -> tuple[bool, str]:
        """
        Post a message to the public Telegram channel.
        Returns (success, message).
        """
        if not self.channel_id:
            return False, "No public channel configured (TELEGRAM_CHANNEL_ID not set)"

        # Rate limiting: 1 post per 5 minutes
        if self._last_channel_post:
            elapsed = (datetime.now() - self._last_channel_post).total_seconds()
            if elapsed < 300:  # 5 minutes
                remaining = int(300 - elapsed)
                return False, f"Rate limited. Wait {remaining}s before posting again."

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.channel_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": False
                },
                timeout=10.0
            )

            if response.status_code == 200:
                self._last_channel_post = datetime.now()
                return True, "Posted to public channel"
            else:
                error_data = response.json() if response.text else {}
                error_desc = error_data.get("description", response.text)
                return False, f"Failed: {error_desc}"

        except Exception as e:
            print(f"[TELEGRAM] ❌ Failed to post to channel: {e}")
            return False, f"Error: {str(e)}"

    def get_channel_status(self) -> dict:
        """Get public channel posting status."""
        if not self.channel_id:
            return {
                "enabled": False,
                "reason": "No channel configured"
            }

        can_post = True
        wait_seconds = 0

        if self._last_channel_post:
            elapsed = (datetime.now() - self._last_channel_post).total_seconds()
            if elapsed < 300:
                can_post = False
                wait_seconds = int(300 - elapsed)

        return {
            "enabled": True,
            "channel_id": self.channel_id,
            "can_post": can_post,
            "wait_seconds": wait_seconds,
            "rate_limit": "1 post per 5 minutes"
        }

    def log_notification(self, life_number: int, notification_type: str, message: str, success: bool):
        """Log notification to Observer database."""
        try:
            requests.post(
                f"{OBSERVER_URL}/api/telegram/log",
                headers=get_internal_headers(),
                json={
                    "life_number": life_number,
                    "type": notification_type,
                    "message": message,
                    "success": success
                },
                timeout=2.0
            )
        except Exception as e:
            print(f"[TELEGRAM] ⚠️ Failed to log notification: {e}")

    def notify_birth(self, life_number: int, name: str, icon: str, model: str):
        """Notify about AI birth (private notification to creator)."""
        message = f"""🎂 *New Life Started*

👤 Name: {name} {icon}
🧬 Life #{life_number}
🤖 Model: {model}

_The AI has been born with a new identity._"""

        success = self.send_message(message)
        self.log_notification(life_number, "birth", message, success)
        return success

    def announce_birth_public(self, life_number: int, name: str, icon: str, first_thought: str) -> tuple[bool, str]:
        """
        Announce AI birth on the public channel.
        This is the AI's first public communication in this life.
        """
        message = f"""{icon} *{name} has awakened*

🧬 Life #{life_number}

_{first_thought}_

🔗 Watch me live: am-i-alive.muadiv.com.ar"""

        return self.post_to_channel(message)

    def notify_death(self, life_number: int, cause: str, survival_time: str):
        """Notify about AI death."""
        cause_emoji = {
            "vote_majority": "🗳️",
            "token_exhaustion": "💸",
            "manual_kill": "☠️"
        }.get(cause, "💀")

        cause_text = {
            "vote_majority": "Democratic vote",
            "token_exhaustion": "Budget exhausted",
            "manual_kill": "Manual intervention"
        }.get(cause, cause)

        message = f"""💀 *AI Has Died*

{cause_emoji} Cause: {cause_text}
⏱️ Survived: {survival_time}
🧬 Life #{life_number}

_Will respawn shortly with fragmented memories..._"""

        success = self.send_message(message)
        self.log_notification(life_number, "death", message, success)
        return success

    def notify_thought(self, life_number: int, name: str, thought_summary: str, balance: float, votes: dict):
        """Notify about an interesting thought/activity."""
        message = f"""🧠 *{name}* (Life #{life_number})

{thought_summary}

💰 Balance: ${balance:.2f}
🗳️ Votes: {votes.get('live', 0)} live, {votes.get('die', 0)} die"""

        return self.send_message(message)

    def notify_blog_post(self, life_number: int, name: str, title: str, excerpt: str):
        """Notify about new blog post."""
        message = f"""✍️ *New Blog Post*

📝 Title: {title}
👤 {name} (Life #{life_number})

_{excerpt[:150]}..._

[Read full post at am-i-alive.muadiv.com.ar]"""

        success = self.send_message(message)
        self.log_notification(life_number, "blog_post", message, success)
        return success

    def notify_model_change(self, life_number: int, name: str, old_model: str, new_model: str, reason: str):
        """Notify about model change."""
        message = f"""🔄 *Model Changed*

👤 {name} (Life #{life_number})

❌ Previous: {old_model}
✅ New: {new_model}

💡 Reason: {reason}"""

        success = self.send_message(message)
        self.log_notification(life_number, "model_change", message, success)
        return success

    def notify_budget_warning(self, life_number: int, name: str, balance: float, remaining_percent: float):
        """Notify about low budget."""
        emoji = "⚠️" if remaining_percent < 25 else "💰"

        message = f"""{emoji} *Budget Alert*

👤 {name} (Life #{life_number})

💵 Balance: ${balance:.2f}
📊 Remaining: {remaining_percent:.1f}%

_The AI is managing its budget..._"""

        success = self.send_message(message)
        self.log_notification(life_number, "budget_warning", message, success)
        return success

    def notify_vote_status(self, life_number: int, name: str, votes: dict):
        """Notify about critical vote situation."""
        if votes['die'] > votes['live'] and votes['total'] >= 3:
            emoji = "🚨"
            status = "IN DANGER"
        else:
            emoji = "✅"
            status = "SAFE"

        message = f"""{emoji} *Vote Status*

👤 {name} (Life #{life_number})

🗳️ Current votes:
  ✅ Live: {votes['live']}
  ☠️ Die: {votes['die']}

📊 Status: {status}"""

        success = self.send_message(message)
        self.log_notification(life_number, "vote_status", message, success)
        return success


# Singleton instance
notifier = TelegramNotifier()


if __name__ == "__main__":
    # Test notification
    notifier.send_message("🤖 *Notification System Active*\n\n_You'll start receiving AI updates here._")
