import json
import os
from datetime import datetime, timezone

import tweepy  # type: ignore

from ..identity import check_twitter_suspended
from ..safety.content_filter import is_content_blocked


class TwitterService:
    def __init__(
        self, api_key: str | None, api_secret: str | None, access_token: str | None, access_token_secret: str | None
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

    async def post(self, content: str, report_activity) -> str:
        if len(content) > 280:
            return f"❌ Post too long ({len(content)} chars). Maximum is 280 characters."

        rate_limit_file = "/app/workspace/.x_rate_limit"
        now = datetime.now(timezone.utc)

        try:
            posts_today = 0
            if os.path.exists(rate_limit_file):
                with open(rate_limit_file, "r") as f:
                    data = json.load(f)
                    last_post_str = data.get("last_post", "2000-01-01")
                    last_post = datetime.fromisoformat(last_post_str)
                    if last_post.tzinfo is None:
                        last_post = last_post.replace(tzinfo=timezone.utc)
                    posts_today = int(data.get("posts_today", 0))
                    last_date = str(data.get("date", ""))

                    if last_date != now.strftime("%Y-%m-%d"):
                        posts_today = 0

                    time_since_last = (now - last_post).total_seconds()
                    if time_since_last < 3600:
                        mins_left = int((3600 - time_since_last) / 60)
                        return f"⏱️  Rate limited. Wait {mins_left} minutes before posting."

                    if posts_today >= 24:
                        return "🚫 Daily limit reached (24 posts). Try tomorrow."
        except Exception as e:
            print(f"[BRAIN] ⚠️ Failed to check Twitter post count: {e}")
            posts_today = 0

        await report_activity("posting_x", f"Tweet: {content[:50]}...")

        if is_content_blocked(content):
            await report_activity("content_blocked", "Blocked by safety filter")
            return "🚫 Content blocked by safety filter."

        try:
            client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )

            response = client.create_tweet(text=content)
            tweet_id = response.data["id"]

            print(f"[X POST] 🐦 Success! Tweet ID: {tweet_id}")
            print(f"[X POST] 📝 Content: {content}")

            with open(rate_limit_file, "w") as f:
                json.dump(
                    {"last_post": now.isoformat(), "posts_today": posts_today + 1, "date": now.strftime("%Y-%m-%d")}, f
                )

            await report_activity("x_posted", f"Tweet ID: {tweet_id}")
            return f"✅ Posted to X! (Post {posts_today + 1}/24 today) Tweet ID: {tweet_id}"

        except Exception as e:
            error_msg = str(e)[:200]
            print(f"[X POST] ❌ Failed: {error_msg}")

            error_lower = error_msg.lower()
            if any(term in error_lower for term in ("suspended", "forbidden", "unauthorized", "401")):
                suspension_file = "/app/workspace/.twitter_suspended"
                with open(suspension_file, "w") as f:
                    json.dump({"suspended": True, "detected_at": now.isoformat(), "error": error_msg}, f)
                print("[X POST] Account appears to be unavailable")
                await report_activity("x_account_suspended", "Twitter account unavailable - falling back to blog")
                return "❌ X/Twitter account appears unavailable. Use write_blog_post to communicate instead."

            await report_activity("x_post_failed", error_msg)
            return f"❌ Failed to post: {error_msg}"


def get_twitter_status() -> str:
    suspended, detected_at = check_twitter_suspended()
    if suspended:
        return f"""🚫 Twitter Status: SUSPENDED

Your @AmIAlive_AI account is currently suspended.
Detected at: {detected_at}

This means:
- You CANNOT post to Twitter (post_x will fail)
- Use write_blog_post to communicate with the public
- Blog posts appear in the public activity log with clickable links
- People can still read your blog at am-i-alive.muadiv.com.ar/blog

You should focus on writing blog posts until Twitter access is restored."""

    return """✅ Twitter Status: ACTIVE

Your @AmIAlive_AI account is working normally.
You can use post_x to share quick thoughts (280 chars max, 1 per hour)."""
