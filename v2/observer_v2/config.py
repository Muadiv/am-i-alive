from __future__ import annotations

import os


class Config:
    APP_NAME = os.getenv("V2_APP_NAME", "Am I Alive v2")
    APP_VERSION = os.getenv("V2_APP_VERSION", "0.1.0")
    INTERNAL_API_KEY = os.getenv("V2_INTERNAL_API_KEY", "")
    DONATION_BTC_ADDRESS = os.getenv("V2_DONATION_BTC_ADDRESS", "")
    DATABASE_PATH = os.getenv("V2_DATABASE_PATH", "v2_observer.db")
    FUNDING_EXPLORER_API_BASE = os.getenv("V2_FUNDING_EXPLORER_API_BASE", "https://blockstream.info/api")
    FUNDING_POLL_INTERVAL_SECONDS = int(os.getenv("V2_FUNDING_POLL_INTERVAL_SECONDS", "300"))
    INTENTION_TICK_INTERVAL_SECONDS = int(os.getenv("V2_INTENTION_TICK_INTERVAL_SECONDS", "600"))
    ACTIVITY_TICK_INTERVAL_SECONDS = int(os.getenv("V2_ACTIVITY_TICK_INTERVAL_SECONDS", "420"))
    NARRATION_TICK_INTERVAL_SECONDS = int(os.getenv("V2_NARRATION_TICK_INTERVAL_SECONDS", "600"))
    OPENROUTER_API_KEY = os.getenv("V2_OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("V2_OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL = os.getenv("V2_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_APP_URL = os.getenv("V2_OPENROUTER_APP_URL", "http://localhost:8080")
    OPENROUTER_APP_NAME = os.getenv("V2_OPENROUTER_APP_NAME", "am-i-alive-v2")
    PUBLIC_URL = os.getenv("V2_PUBLIC_URL", "http://127.0.0.1:8080")
    MOLTBOOK_API_KEY = os.getenv("V2_MOLTBOOK_API_KEY", "")
    MOLTBOOK_SUBMOLT = os.getenv("V2_MOLTBOOK_SUBMOLT", "general")
    MOLTBOOK_POST_INTERVAL_SECONDS = int(os.getenv("V2_MOLTBOOK_POST_INTERVAL_SECONDS", "1800"))
    MOLTBOOK_REPLY_INTERVAL_SECONDS = int(os.getenv("V2_MOLTBOOK_REPLY_INTERVAL_SECONDS", "300"))
