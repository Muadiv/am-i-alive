"""
Telegram Notifier for Am I Alive?

Sends activity summaries to the creator's Telegram for easy sharing on social media.
Uses free Gemini Flash model to generate concise summaries.
"""

import os
import requests
from typing import Optional

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OBSERVER_URL = os.getenv("OBSERVER_URL", "http://observer:8080")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable must be set")
if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID environment variable must be set")


def get_internal_headers() -> dict:
    """Headers for Observer internal endpoints."""
    if INTERNAL_API_KEY:
        return {"X-Internal-Key": INTERNAL_API_KEY}
    return {}


class TelegramNotifier:
    """Sends notifications to Telegram."""

    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a text message to Telegram."""
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
        """Notify about AI birth."""
        message = f"""🎂 *New Life Started*

👤 Name: {name} {icon}
🧬 Life #{life_number}
🤖 Model: {model}

_The AI has been born with a new identity._"""

        success = self.send_message(message)
        self.log_notification(life_number, "birth", message, success)
        return success

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
