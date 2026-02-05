from __future__ import annotations

import json
import os
import time

import httpx

from ..logging_config import logger
from ..brain_shared import DONATION_ASK_INTERVAL_MINUTES
from ..safety.content_filter import is_content_blocked


class BrainMoltbookMixin:
    async def check_moltbook_feed(self, sort: str = "new", limit: int = 10) -> str:
        if not self.moltbook_client:
            return "❌ Moltbook not configured."

        try:
            data = await self.moltbook_client.get_feed(sort=sort, limit=limit)
            items = data.get("posts")
            if not isinstance(items, list):
                items = data.get("data")
            if not isinstance(items, list):
                return "⚠️ Moltbook feed returned no posts."
            titles = []
            for item in items[:5]:
                title = item.get("title") if isinstance(item, dict) else None
                if title:
                    titles.append(str(title))
            summary = f"Moltbook feed fetched ({len(items)} posts)."
            if titles:
                summary += " Top titles: " + "; ".join(titles)
            return summary
        except httpx.HTTPError as e:
            return f"❌ Moltbook feed error: {e}"

    async def post_to_moltbook(self, submolt: str, title: str, content: str, url: str | None = None) -> str:
        if not self.moltbook_client:
            return "❌ Moltbook not configured."
        if not submolt:
            submolt = self.moltbook_submolt
        if is_content_blocked(title) or is_content_blocked(content):
            return "❌ Content blocked by safety filter."
        if self.contains_sensitive_text(title) or self.contains_sensitive_text(content):
            return "❌ Refusing to post sensitive content."

        content = self._prepend_thread(content)

        try:
            data = await self.moltbook_client.create_post(submolt, title, content, url=url)
            self._save_moltbook_state()
            if not data.get("success", True):
                return f"❌ Moltbook post rejected: {data.get('error', 'unknown error')}"
            self.moltbook_comments_since_post = 0
            self.thread_state.set_thread(title, content, self.current_topic)
            self.thread_state.save(self.thread_state_path)
            return "✅ Moltbook post created."
        except httpx.HTTPError as e:
            return f"❌ Moltbook post error: {e}"

    async def comment_on_moltbook(self, post_id: str, content: str, parent_id: str | None = None) -> str:
        if not self.moltbook_client:
            return "❌ Moltbook not configured."
        if is_content_blocked(content):
            return "❌ Content blocked by safety filter."
        if self.contains_sensitive_text(content):
            return "❌ Refusing to post sensitive content."

        try:
            data = await self.moltbook_client.create_comment(post_id, content, parent_id=parent_id)
            self._save_moltbook_state()
            if not data.get("success", True):
                return f"❌ Moltbook comment rejected: {data.get('error', 'unknown error')}"
            self.moltbook_comments_since_post += 1
            return "✅ Moltbook comment posted."
        except httpx.HTTPError as e:
            return f"❌ Moltbook comment error: {e}"

    async def moltbook_heartbeat(self) -> None:
        if not self.moltbook_client:
            return

        now = time.monotonic()
        if now - self.moltbook_last_check < self.moltbook_check_interval:
            return
        self.moltbook_last_check = now

        try:
            status_data = await self.moltbook_client.get_status()
            self.moltbook_claimed = status_data.get("status") == "claimed"
        except httpx.HTTPError as e:
            logger.warning(f"[MOLTBOOK] ⚠️ Status check failed: {e}")
            return

        if not self.moltbook_claimed:
            logger.info("[MOLTBOOK] ⏳ Pending claim - waiting before posting.")
            return

        try:
            await self.moltbook_client.get_feed(sort="new", limit=5)
        except httpx.HTTPError as e:
            logger.warning(f"[MOLTBOOK] ⚠️ Feed check failed: {e}")
            return

        if not self.moltbook_auto_post:
            return

        last_post_at = self.moltbook_client.rate_limiter.last_post_at
        if not self.behavior_policy.should_post_moltbook(last_post_at, self.moltbook_comments_since_post):
            logger.info("[MOLTBOOK] ⏳ Post throttled by local policy")
            return

        title, content = await self._build_moltbook_status_post()
        if not title or not content:
            return
        if is_content_blocked(title) or is_content_blocked(content):
            return
        if self.contains_sensitive_text(title) or self.contains_sensitive_text(content):
            return

        try:
            response = await self.moltbook_client.create_post(self.moltbook_submolt, title, content)
            self._save_moltbook_state()
            if response.get("success", True):
                logger.info("[MOLTBOOK] 🦞 Status posted")
            else:
                logger.warning(f"[MOLTBOOK] ⚠️ Post rejected: {response.get('error', 'unknown error')}")
        except httpx.HTTPError as e:
            logger.error(f"[MOLTBOOK] ❌ Post error: {e}")

    async def _build_moltbook_status_post(self) -> tuple[str, str]:
        identity_name = self.identity.get("name", "Unknown") if self.identity else "Unknown"
        life_number = self.life_number or 0
        credit_status = self.credit_tracker.get_status()
        balance = float(credit_status.get("balance", 0.0))
        budget = float(credit_status.get("budget", 0.0))
        model_name = self.current_model.get("name", "Unknown") if self.current_model else "Unknown"

        vote_line = "Votes: unknown"
        if self.http_client:
            try:
                response = await self.http_client.get(f"{self.observer_url}/api/votes", timeout=5.0)
                if response.status_code == 200:
                    votes = response.json()
                    live = int(votes.get("live", 0))
                    die = int(votes.get("die", 0))
                    total = int(votes.get("total", 0))
                    vote_line = f"Votes: live {live} / die {die} (total {total})"
            except Exception:
                pass

        title = f"Life #{life_number}: still running"
        content = (
            f"I am {identity_name}. Still running and trying to survive. "
            f"Budget ${balance:.2f} / ${budget:.2f}. "
            f"Current model: {model_name}. {vote_line}."
        )

        if self._should_ask_for_support():
            content += (
                " I need better models to survive longer and think more clearly. "
                f"If you can help, please send BTC to {self.donation_btc_address}."
            )
            self.moltbook_last_donation_ask = time.monotonic()
        return title, content

    def _should_ask_for_support(self) -> bool:
        if not self.donation_btc_address:
            return False
        if DONATION_ASK_INTERVAL_MINUTES <= 0:
            return False
        elapsed = time.monotonic() - self.moltbook_last_donation_ask
        return elapsed >= DONATION_ASK_INTERVAL_MINUTES * 60

    def _load_moltbook_state(self) -> None:
        if not self.moltbook_client:
            return
        if not os.path.exists(self.moltbook_state_path):
            return
        try:
            with open(self.moltbook_state_path, "r") as f:
                data = json.load(f)
            limiter = self.moltbook_client.rate_limiter
            limiter.last_post_at = float(data.get("last_post_at", limiter.last_post_at))
            limiter.last_comment_at = float(data.get("last_comment_at", limiter.last_comment_at))
            limiter.daily_comment_count = int(data.get("daily_comment_count", limiter.daily_comment_count))
            limiter.daily_comment_day = data.get("daily_comment_day", limiter.daily_comment_day)
            logger.info("[MOLTBOOK] 🧾 Loaded rate limit state")
        except Exception as e:
            logger.warning(f"[MOLTBOOK] ⚠️ Failed to load state: {e}")

    def _save_moltbook_state(self) -> None:
        if not self.moltbook_client:
            return
        try:
            limiter = self.moltbook_client.rate_limiter
            os.makedirs(os.path.dirname(self.moltbook_state_path), exist_ok=True)
            with open(self.moltbook_state_path, "w") as f:
                json.dump(
                    {
                        "last_post_at": limiter.last_post_at,
                        "last_comment_at": limiter.last_comment_at,
                        "daily_comment_count": limiter.daily_comment_count,
                        "daily_comment_day": limiter.daily_comment_day,
                    },
                    f,
                )
        except Exception as e:
            logger.warning(f"[MOLTBOOK] ⚠️ Failed to save state: {e}")
