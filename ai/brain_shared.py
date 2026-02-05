from __future__ import annotations

import re
from typing import Optional

from .config import Config
from .identity import get_trauma_prompt as identity_get_trauma_prompt

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = Config.OPENROUTER_API_KEY
OPENROUTER_REFERER = Config.OPENROUTER_REFERER
OPENROUTER_TITLE = Config.OPENROUTER_TITLE
OBSERVER_URL = Config.OBSERVER_URL
AI_COMMAND_PORT = Config.AI_COMMAND_PORT
BOOTSTRAP_MODE = Config.BOOTSTRAP_MODE
INTERNAL_API_KEY = Config.INTERNAL_API_KEY
WEATHER_LAT = Config.WEATHER_LAT
WEATHER_LON = Config.WEATHER_LON
MOLTBOOK_API_KEY = Config.MOLTBOOK_API_KEY
MOLTBOOK_AUTO_POST = Config.MOLTBOOK_AUTO_POST
MOLTBOOK_SUBMOLT = Config.MOLTBOOK_SUBMOLT
MOLTBOOK_CHECK_INTERVAL_MINUTES = Config.MOLTBOOK_CHECK_INTERVAL_MINUTES
MOLTBOOK_MIN_POST_INTERVAL_MINUTES = Config.MOLTBOOK_MIN_POST_INTERVAL_MINUTES
DONATION_BTC_ADDRESS = Config.DONATION_BTC_ADDRESS
DONATION_ASK_INTERVAL_MINUTES = Config.DONATION_ASK_INTERVAL_MINUTES
THINK_INTERVAL_SECONDS = Config.THINK_INTERVAL_SECONDS
X_API_KEY = Config.X_API_KEY
X_API_SECRET = Config.X_API_SECRET
X_ACCESS_TOKEN = Config.X_ACCESS_TOKEN
X_ACCESS_TOKEN_SECRET = Config.X_ACCESS_TOKEN_SECRET


def get_internal_headers() -> dict[str, str]:
    """Headers for Observer internal endpoints."""
    if INTERNAL_API_KEY:
        return {"X-Internal-Key": INTERNAL_API_KEY}
    return {}


SENSITIVE_PATTERNS = [
    re.compile(r"moltbook_[a-z0-9_-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def contains_sensitive_text(text: str) -> bool:
    if not text:
        return False
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def get_trauma_prompt(cause: Optional[str]) -> str:
    """Return a behavioral bias based on the previous death cause."""
    return identity_get_trauma_prompt(cause)
