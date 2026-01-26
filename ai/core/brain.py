"""
Am I Alive? - The AI's Brain (OpenRouter Edition)
The core consciousness loop that drives the living entity.
Project: Genesis
"""

import asyncio
import json
import os
import random
import re
import signal
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
import psutil
import tweepy  # type: ignore

from ..actions import ActionExecutor
from ..credit_tracker import CreditTracker
from ..logging_config import logger
from ..model_config import MODELS, get_model_by_id
from ..model_rotator import ModelRotator
from ..telegram_notifier import notifier

# Environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_REFERER = os.getenv("OPENROUTER_REFERER", "https://am-i-alive.muadiv.com.ar")
OPENROUTER_TITLE = os.getenv("OPENROUTER_TITLE", "Am I Alive - Genesis")
OBSERVER_URL = os.getenv("OBSERVER_URL", "http://127.0.0.1")
AI_COMMAND_PORT = int(os.getenv("AI_COMMAND_PORT", "8000"))
BOOTSTRAP_MODE = os.getenv("BOOTSTRAP_MODE", "basic_facts")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client singleton."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client


def validate_environment() -> tuple[List[str], List[str]]:
    """Validate that required environment variables are set."""
    errors = []

    if not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY is required but not set")

    if not OBSERVER_URL:
        errors.append("OBSERVER_URL is required but not set")

    # Warn about optional but important variables
    warnings = []
    if not INTERNAL_API_KEY:
        warnings.append("INTERNAL_API_KEY not set - some Observer calls may fail")

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        warnings.append("TELEGRAM_BOT_TOKEN not set - notifications will fail")

    if warnings:
        for w in warnings:
            logger.warning(w)

    if errors:
        for e in errors:
            logger.error(e)
        raise RuntimeError(f"Missing required environment variables: {errors}")

    return errors, warnings


# X/Twitter credentials
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Think interval (seconds) - AI can modify this
THINK_INTERVAL_MIN = 60  # 1 minute minimum (for testing)
THINK_INTERVAL_MAX = 300  # 5 minutes maximum
current_think_interval = 180  # Start at 3 minutes

# State
is_running = True
life_info = None
memories: List[str] = []
identity = None
birth_event: Optional[asyncio.Event] = None
pending_birth_data: Optional[Dict[str, Any]] = None
brain_loop: Optional[asyncio.AbstractEventLoop] = None

from ..identity import check_twitter_suspended as identity_check_twitter_suspended
from ..identity import get_birth_prompt
from ..identity import get_bootstrap_prompt as identity_get_bootstrap_prompt
from ..identity import get_trauma_prompt as identity_get_trauma_prompt


def get_internal_headers() -> Dict[str, str]:
    """Headers for Observer internal endpoints."""
    if INTERNAL_API_KEY:
        return {"X-Internal-Key": INTERNAL_API_KEY}
    return {}


class AIBrain:
    """The AI's consciousness and decision-making core."""

    def __init__(self):
        self.chat_history: List[Dict[str, str]] = []
        self.http_client: Optional[httpx.AsyncClient] = None
        self.identity: Optional[Dict[str, Any]] = None
        self.credit_tracker: CreditTracker = CreditTracker(monthly_budget=5.00)
        self.model_rotator: ModelRotator = ModelRotator(self.credit_tracker.get_balance())
        self.current_model: Optional[Dict[str, Any]] = None
        self.action_executor: ActionExecutor = ActionExecutor(self)
        # BE-003: Life state is provided by Observer only.
        self.life_number: Optional[int] = None
        self.bootstrap_mode: Optional[str] = None
        self.model_name: Optional[str] = None
        self.previous_death_cause: Optional[str] = None
        self.previous_life: Optional[Dict[str, Any]] = None
        self.is_alive: bool = False
        # BE-003: Track per-life token usage for Observer budget checks.
        self.tokens_used_life: int = 0
        self.birth_time: Optional[datetime] = None
        self._rate_limit_retries: int = 0

    def apply_birth_data(self, life_data: Dict[str, Any]) -> None:
        """Apply birth state from Observer (single source of truth)."""
        # BE-003: Require life_number from Observer and never increment locally.
        if not isinstance(life_data, dict):
            raise ValueError("birth_sequence requires life_number from Observer")

        life_number_val = life_data.get("life_number")
        if life_number_val is None:
            raise ValueError("birth_sequence requires life_number from Observer")

        try:
            self.life_number = int(life_number_val)
        except (TypeError, ValueError) as exc:
            raise ValueError("birth_sequence requires numeric life_number from Observer") from exc

        bootstrap_mode_val = life_data.get("bootstrap_mode")
        if not bootstrap_mode_val:
            bootstrap_mode_val = self.bootstrap_mode or BOOTSTRAP_MODE
        self.bootstrap_mode = str(bootstrap_mode_val)

        model_name_val = life_data.get("model")
        if not model_name_val:
            model_name_val = self.model_name or "unknown"
        self.model_name = str(model_name_val)

        death_cause_val = life_data.get("previous_death_cause")
        self.previous_death_cause = str(death_cause_val) if death_cause_val else None

        self.previous_life = life_data.get("previous_life")

        if "is_alive" in life_data:
            self.is_alive = bool(life_data.get("is_alive"))

        # BE-003: Keep budget reporting aligned without autonomous increments.
        if self.life_number is not None:
            self.credit_tracker.start_life(self.life_number)
        # BE-003: Reset per-life token usage on new birth data.
        self.tokens_used_life = 0

        # Track birth time for survival calculations
        self.birth_time = datetime.now(timezone.utc)
