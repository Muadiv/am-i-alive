from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import random
from datetime import datetime, timezone

from .integration_state import IntegrationStateStore
from .moltbook_formatter import build_post_content, build_reply_content
from .moltbook_publisher import MoltbookPublisher
from .moments import MomentsStore
from .storage import SqliteStorage


@dataclass
class MoltbookService:
    storage: SqliteStorage
    moments: MomentsStore
    integration_state: IntegrationStateStore
    publisher: MoltbookPublisher
    api_key: str
    public_url: str
    donation_btc_address: str

    async def tick_publish_once(self, force: bool = False) -> dict[str, object]:
        if not self.api_key.strip():
            result = {"success": False, "error": "missing_api_key"}
            self._set_status("publish", result)
            return result

        pending = self._get_pending_post()
        if pending:
            retry_result = await self._publish_with_retries(
                title=str(pending.get("title", "")),
                content=str(pending.get("content", "")),
                max_attempts=3,
            )
            if retry_result.get("success"):
                self._clear_pending_post()
                self._set_status("publish", {"success": True, "mode": "pending_recovered", **retry_result})
                return {"success": True, "mode": "pending_recovered", **retry_result}

        latest = self.moments.latest_public_of_types(["activity", "narration"])
        if not latest:
            result = {"success": False, "error": "no_moments"}
            self._set_status("publish", result)
            return result

        moment_id = int(latest["id"])
        posted_raw = self.integration_state.get_value("moltbook_last_moment_id")
        posted_id = int(posted_raw) if posted_raw and posted_raw.isdigit() else 0
        if not force and moment_id <= posted_id:
            return {"success": True, "skipped": True, "reason": "already_posted"}

        state = self.storage.get_life_state()
        vote_round = self.storage.get_open_vote_round()
        title = f"[Life {state['life_number']}] {latest['title']}"
        content = build_post_content(
            latest_title=str(latest["title"]),
            latest_content=str(latest["content"]),
            life_number=int(state["life_number"]),
            state=str(state["state"]),
            intention=str(state["current_intention"]),
            live_votes=int(vote_round.get("live", 0)),
            die_votes=int(vote_round.get("die", 0)),
            public_url=self.public_url,
            btc_address=self.donation_btc_address,
        )
        result = await self._publish_with_retries(title=title, content=content, max_attempts=3)
        if result.get("success"):
            self.integration_state.set_value("moltbook_last_moment_id", str(moment_id))
            post_payload = result.get("post", {})
            if isinstance(post_payload, dict):
                post_id = str(post_payload.get("id", "")).strip()
                if post_id:
                    self.integration_state.set_value("moltbook_last_post_id", post_id)
            self._clear_pending_post()
            self._set_status("publish", result)
            return result

        self._set_pending_post({"title": title, "content": content, "moment_id": moment_id})
        self._set_status("publish", result)
        return result

    async def tick_replies_once(self, force: bool = False) -> dict[str, object]:
        if not self.api_key.strip():
            result = {"success": False, "error": "missing_api_key"}
            self._set_status("replies", result)
            return result

        post_id = self.integration_state.get_value("moltbook_last_post_id")
        comments: list[dict[str, object]] = []
        if post_id:
            comments_payload = await asyncio.to_thread(self.publisher.get_post_comments, post_id, 30)
            if comments_payload.get("success"):
                comments = _extract_comments(comments_payload)

        replied_set = _load_replied_comment_ids(self.integration_state.get_value("moltbook_replied_comment_ids"))
        replied_posts = _load_replied_comment_ids(self.integration_state.get_value("moltbook_replied_post_ids"))
        replied_now = 0

        for comment in comments:
            comment_id = str(comment.get("id", "")).strip()
            comment_text = str(comment.get("content", "")).strip()
            if not comment_id or comment_id in replied_set:
                continue
            if "am-i-alive v2" in comment_text.lower():
                continue

            reply_text = build_reply_content(comment_text, self.public_url, self.donation_btc_address)
            result = await asyncio.to_thread(self.publisher.create_comment, post_id, reply_text, comment_id)
            if not result.get("success"):
                if not force:
                    break
                continue

            replied_set.add(comment_id)
            replied_now += 1
            if replied_now >= 3 and not force:
                break

        self.integration_state.set_value("moltbook_replied_comment_ids", json.dumps(sorted(replied_set)[-300:]))

        feed_payload = await asyncio.to_thread(self.publisher.get_feed, 20)
        if feed_payload.get("success"):
            posts = _extract_posts(feed_payload)
            for post in posts:
                post_key = str(post.get("id", "")).strip()
                if not post_key or post_key in replied_posts:
                    continue
                if post_id and post_key == post_id:
                    continue

                source_text = str(post.get("title", "")).strip() or str(post.get("content", "")).strip()
                if not source_text:
                    continue
                reply_text = build_reply_content(source_text, self.public_url, self.donation_btc_address)
                reply_result = await asyncio.to_thread(self.publisher.create_comment, post_key, reply_text, None)
                if not reply_result.get("success"):
                    if not force:
                        break
                    continue

                replied_posts.add(post_key)
                replied_now += 1
                if replied_now >= 4 and not force:
                    break

        self.integration_state.set_value("moltbook_replied_post_ids", json.dumps(sorted(replied_posts)[-300:]))
        result = {"success": True, "replied": replied_now, "scanned": len(comments)}
        self._set_status("replies", result)
        return result

    def get_status(self) -> dict[str, object]:
        publish = self._load_json_state("moltbook_status_publish")
        replies = self._load_json_state("moltbook_status_replies")
        pending = self._get_pending_post()
        return {
            "publish": publish,
            "replies": replies,
            "has_pending_post": pending is not None,
        }

    async def _publish_with_retries(self, title: str, content: str, max_attempts: int) -> dict[str, object]:
        attempt = 0
        last_result: dict[str, object] = {"success": False, "error": "unknown"}
        while attempt < max_attempts:
            attempt += 1
            result = await asyncio.to_thread(self.publisher.publish, title, content)
            if result.get("success"):
                return {**result, "attempts": attempt}

            last_result = {**result, "attempts": attempt}
            status_code = int(result.get("status_code", 0)) if str(result.get("status_code", "")).isdigit() else 0
            retriable = status_code in {429, 500, 502, 503, 504} or "Temporary failure" in str(result.get("error", ""))
            if not retriable or attempt >= max_attempts:
                break

            base = min(30.0, 2.0 * (2 ** (attempt - 1)))
            jitter = random.uniform(0.2, 1.1)
            await asyncio.sleep(base + jitter)

        return last_result

    def _set_pending_post(self, payload: dict[str, object]) -> None:
        self.integration_state.set_value("moltbook_pending_post", json.dumps(payload))

    def _clear_pending_post(self) -> None:
        self.integration_state.set_value("moltbook_pending_post", "")

    def _get_pending_post(self) -> dict[str, object] | None:
        raw = self.integration_state.get_value("moltbook_pending_post")
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _set_status(self, channel: str, result: dict[str, object]) -> None:
        key = f"moltbook_status_{channel}"
        state = {
            "at": datetime.now(timezone.utc).isoformat(),
            "success": bool(result.get("success", False)),
            "error": str(result.get("error", "")) if result.get("error") else "",
            "status_code": int(result.get("status_code", 0)) if str(result.get("status_code", "")).isdigit() else 0,
            "attempts": int(result.get("attempts", 0)) if str(result.get("attempts", "")).isdigit() else 0,
            "details": str(result.get("details", ""))[:300],
        }
        self.integration_state.set_value(key, json.dumps(state))

    def _load_json_state(self, key: str) -> dict[str, object]:
        raw = self.integration_state.get_value(key)
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}


def _extract_comments(payload: dict[str, object]) -> list[dict[str, object]]:
    if isinstance(payload.get("comments"), list):
        return [row for row in payload["comments"] if isinstance(row, dict)]
    if isinstance(payload.get("data"), list):
        return [row for row in payload["data"] if isinstance(row, dict)]
    if isinstance(payload.get("data"), dict):
        data = payload["data"]
        comments = data.get("comments", []) if isinstance(data, dict) else []
        if isinstance(comments, list):
            return [row for row in comments if isinstance(row, dict)]
    return []


def _extract_posts(payload: dict[str, object]) -> list[dict[str, object]]:
    if isinstance(payload.get("posts"), list):
        return [row for row in payload["posts"] if isinstance(row, dict)]
    if isinstance(payload.get("data"), list):
        return [row for row in payload["data"] if isinstance(row, dict)]
    if isinstance(payload.get("data"), dict):
        data = payload["data"]
        posts = data.get("posts", []) if isinstance(data, dict) else []
        if isinstance(posts, list):
            return [row for row in posts if isinstance(row, dict)]
    return []


def _load_replied_comment_ids(raw: str | None) -> set[str]:
    if not raw:
        return set()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, list):
        return set()
    return {str(item) for item in parsed if str(item).strip()}
