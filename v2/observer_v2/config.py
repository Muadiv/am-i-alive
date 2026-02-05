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
    NARRATION_TICK_INTERVAL_SECONDS = int(os.getenv("V2_NARRATION_TICK_INTERVAL_SECONDS", "600"))
    OPENROUTER_API_KEY = os.getenv("V2_OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("V2_OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL = os.getenv("V2_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_APP_URL = os.getenv("V2_OPENROUTER_APP_URL", "http://localhost:8080")
    OPENROUTER_APP_NAME = os.getenv("V2_OPENROUTER_APP_NAME", "am-i-alive-v2")
