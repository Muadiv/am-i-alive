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
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

if __name__ == "__main__":
    import sys

    sys.modules.setdefault("ai.brain", sys.modules[__name__])

try:
    from .actions import ActionExecutor
except ImportError:
    from actions import ActionExecutor

# Import our custom modules
from .config import Config
from .core.action_processor import ActionProcessor
from .core.brain_state import BrainState
from .core.lifecycle_dto import LifecycleData
from .credit_tracker import CreditTracker
from .logging_config import logger
from .model_rotator import ModelRotator
from .services.action_handler import ActionHandler
from .services.budget_service import BudgetService
from .services.chat_service import ChatService
from .services.echo_service import EchoService
from .services.health_check_service import HealthCheckService
from .services.http_client_factory import HttpClientFactory
from .services.lifecycle_coordinator import LifecycleCoordinator
from .services.lifecycle_service import LifecycleService
from .services.model_retry_policy import ModelRetryPolicy
from .services.observer_client import ObserverClient
from .services.oracle_service import OracleService
from .services.prompt_service import PromptService
from .services.reporting_service import ReportingService
from .services.sandbox_service import SandboxService
from .services.self_model_service import SelfModelService
from .services.system_check_service import SystemCheckService
from .services.system_stats_service import SystemStatsService
from .services.twitter_service import TwitterService, get_twitter_status
from .services.weather_service import WeatherService
from .services.behavior_policy import BehaviorPolicy
from .services.memory_selector import MemorySelector
from .telegram_notifier import notifier
from .moltbook_client import MoltbookClient
from .safety.content_filter import is_content_blocked

# Environment
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

_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = HttpClientFactory.create(timeout=60.0)
    return _http_client


def validate_environment() -> tuple[list[str], list[str]]:
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

    if not Config.TELEGRAM_BOT_TOKEN:
        warnings.append("TELEGRAM_BOT_TOKEN not set - notifications will fail")

    if MOLTBOOK_AUTO_POST and not MOLTBOOK_API_KEY:
        warnings.append("MOLTBOOK_API_KEY not set - Moltbook integration disabled")

    if warnings:
        for w in warnings:
            logger.warning(f"[STARTUP] ⚠️ {w}")

    if errors:
        for e in errors:
            logger.error(f"[STARTUP] ❌ {e}")
        raise RuntimeError(f"Missing required environment variables: {errors}")

    return errors, warnings


# X/Twitter credentials
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Think interval (seconds) - fixed cadence
THINK_INTERVAL_MIN = Config.THINK_INTERVAL_MIN
THINK_INTERVAL_MAX = Config.THINK_INTERVAL_MAX
current_think_interval = Config.DEFAULT_THINK_INTERVAL

# State
is_running = True
life_info = None
memories: list[str] = []
identity = None
# BE-003: Observer-driven birth gating and sync coordination.
birth_event: Optional[asyncio.Event] = None
pending_birth_data: Optional[dict[str, Any]] = None
brain_loop: Optional[asyncio.AbstractEventLoop] = None


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
class AIBrain:
    """The AI's consciousness and decision-making core."""

    def select_content_model(self) -> dict[str, Any] | None:
        if not self.model_rotator:
            return None
        return self.model_rotator.select_best_for_budget(tier="ultra_cheap")

    async def send_message_with_model(self, message: str, model: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if not model:
            return await self.send_message(message)

        previous_model = self.current_model
        self.current_model = model
        try:
            return await self.send_message(message)
        finally:
            self.current_model = previous_model

    def __init__(self) -> None:
        self.chat_history: list[dict[str, str]] = []
        self.http_client: httpx.AsyncClient | None = None
        self.observer_client: ObserverClient | None = None
        self.chat_service: ChatService | None = None
        self.reporting_service: ReportingService | None = None
        self.model_retry_policy: ModelRetryPolicy | None = None
        self.echo_service: EchoService | None = None
        self.identity: dict[str, Any] | None = None
        self.credit_tracker: CreditTracker = CreditTracker(monthly_budget=5.00)
        self.model_rotator: ModelRotator = ModelRotator(self.credit_tracker.get_balance())
        self.current_model: dict[str, Any] | None = None
        self.action_executor: ActionExecutor = ActionExecutor(self)
        self.action_processor = ActionProcessor(
            self.action_executor,
            self.send_message,
            self.report_thought,
            self.send_message_with_model,
            self.select_content_model,
        )
        self.budget_service = BudgetService(self.credit_tracker, self.model_rotator, self.report_activity)
        self.sandbox_service = SandboxService()
        self.prompt_service: PromptService | None = None
        self.self_model_service = SelfModelService("/app/workspace/self_model.json")
        self.oracle_service: OracleService | None = None
        self.lifecycle_service: LifecycleService | None = None
        self.action_handler: ActionHandler | None = None
        self.moltbook_client: MoltbookClient | None = None
        self.moltbook_auto_post: bool = MOLTBOOK_AUTO_POST
        self.moltbook_submolt: str = MOLTBOOK_SUBMOLT
        self.moltbook_check_interval: int = MOLTBOOK_CHECK_INTERVAL_MINUTES * 60
        self.moltbook_last_check: float = 0.0
        self.moltbook_claimed: bool = False
        self.donation_btc_address: str | None = DONATION_BTC_ADDRESS
        self.moltbook_last_donation_ask: float = 0.0
        self.moltbook_state_path = "/app/workspace/moltbook_state.json"
        self.behavior_policy = BehaviorPolicy(
            think_interval_seconds=current_think_interval,
            moltbook_min_post_interval_seconds=max(MOLTBOOK_MIN_POST_INTERVAL_MINUTES * 60, 1800),
        )
        self.memory_selector = MemorySelector()
        # BE-003: Life state is provided by Observer only.
        self.life_number: int | None = None
        self.bootstrap_mode: str | None = None
        self.model_name: str | None = None
        self.previous_death_cause: str | None = None
        self.previous_life: dict[str, Any] | None = None
        self.is_alive: bool = False
        # BE-003: Track per-life token usage for Observer budget checks.
        self.tokens_used_life: int = 0
        self.birth_time: datetime | None = None
        self._rate_limit_retries: int = 0
        self._total_free_failures: int = 0

    def apply_birth_data(self, life_data: dict[str, Any]) -> None:
        """Apply birth state from Observer (single source of truth)."""
        if not isinstance(life_data, dict):
            raise ValueError("birth_sequence requires life_number from Observer")

        dto = LifecycleData.from_payload(life_data)
        self.life_number = dto.life_number

        bootstrap_mode_val = dto.bootstrap_mode or self.bootstrap_mode or BOOTSTRAP_MODE
        self.bootstrap_mode = str(bootstrap_mode_val)
        if self.lifecycle_service:
            self.lifecycle_service.bootstrap_mode = self.bootstrap_mode

        model_name_val = dto.model or self.model_name or "unknown"
        self.model_name = str(model_name_val)

        self.previous_death_cause = dto.previous_death_cause
        self.previous_life = dto.previous_life

        if "is_alive" in life_data:
            self.is_alive = bool(life_data.get("is_alive"))

        # BE-003: Keep budget reporting aligned without autonomous increments.
        if self.life_number is not None:
            self.credit_tracker.start_life(self.life_number)
        # BE-003: Reset per-life token usage on new birth data.
        self.tokens_used_life = 0

        # Track birth time for survival calculations
        self.birth_time = datetime.now(timezone.utc)

    def _build_state(self) -> BrainState:
        model_name = self.current_model.get("name", "unknown") if self.current_model else "unknown"
        return BrainState(
            identity=self.identity,
            model_name=model_name,
            balance=self.credit_tracker.get_balance(),
            life_number=self.life_number,
            bootstrap_mode=self.bootstrap_mode,
        )

    def _estimate_max_chars(self) -> int:
        context_tokens = int(self.current_model.get("context", 32768)) if self.current_model else 32768
        max_chars = int(context_tokens * 4 * 0.85)
        return max(max_chars, 8000)

    def _build_messages(
        self,
        message: str,
        system_prompt: Optional[str],
        max_chars: int,
        max_history_messages: int,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        history = self.chat_history[-max_history_messages:] if max_history_messages > 0 else []
        for msg in history:
            messages.append(msg)

        messages.append({"role": "user", "content": message})

        total_chars = sum(len(entry.get("content", "")) for entry in messages)
        while total_chars > max_chars and len(messages) > 2:
            dropped = messages.pop(1)
            total_chars -= len(dropped.get("content", ""))

        return messages

    def _trim_chat_history(self, max_chars: int, max_messages: int) -> None:
        if len(self.chat_history) > max_messages:
            self.chat_history = self.chat_history[-max_messages:]

        total_chars = sum(len(entry.get("content", "")) for entry in self.chat_history)
        while total_chars > max_chars and len(self.chat_history) > 2:
            dropped = self.chat_history.pop(0)
            total_chars -= len(dropped.get("content", ""))

    async def send_message(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        max_history_messages: int | None = None,
        max_chars: int | None = None,
        context_retry: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """
        Send a message to OpenRouter and track token usage.
        Returns: (response_text, usage_stats)
        """
        # Select model if not set
        if not self.current_model:
            self.current_model = self.model_rotator.select_random_model()
            logger.info(f"[BRAIN] 🧠 Selected model: {self.current_model['name']}")

        current_model = self.current_model

        max_chars = max_chars or self._estimate_max_chars()
        max_history_messages = max_history_messages or 40
        messages = self._build_messages(message, system_prompt, max_chars, max_history_messages)

        # Make API call to OpenRouter
        try:
            if not self.chat_service:
                raise RuntimeError("Chat service not initialized")

            data = await self.chat_service.send(current_model["id"], messages)
            response_text, usage = self.chat_service.extract_response(data)
            input_tokens, output_tokens = self.chat_service.extract_usage(usage)
            # BE-003: Track per-life token usage for Observer budget checks.
            self.tokens_used_life += input_tokens + output_tokens

            # Track costs
            status_level = self.credit_tracker.charge(
                current_model["id"],
                input_tokens,
                output_tokens,
                float(current_model["input_cost"]),
                float(current_model["output_cost"]),
            )

            # Update chat history
            self.chat_history.append({"role": "user", "content": message})
            self.chat_history.append({"role": "assistant", "content": response_text})

            # Keep history manageable within model context
            self._trim_chat_history(self._estimate_max_chars(), 40)

            # Update rotator's balance
            self.model_rotator.credit_balance = self.credit_tracker.get_balance()
            # Reset failure tracking for successful model call
            if self.current_model:
                self.model_rotator.reset_free_failure(self.current_model["id"])

            remaining_balance = self.credit_tracker.get_balance()
            cost = (input_tokens / 1_000_000) * float(current_model["input_cost"]) + (
                output_tokens / 1_000_000
            ) * float(current_model["output_cost"])

            usage_stats: dict[str, Any] = {
                "model": current_model["name"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
                "balance": remaining_balance,
                "status": status_level,
            }

            logger.info(
                "[BRAIN] 💰 Usage: "
                f"{usage_stats['total_tokens']} tokens, ${usage_stats['cost']:.4f}, "
                f"Balance: ${usage_stats['balance']:.2f}"
            )

            return response_text, usage_stats
        except httpx.HTTPStatusError as e:
            error_code = e.response.status_code
            error_text = e.response.text
            logger.error(f"[BRAIN] ❌ HTTP Error: {error_code} - {error_text}")

            if error_code == 400 and "context length" in error_text.lower() and not context_retry:
                logger.warning("[BRAIN] ⚠️ Context too long; retrying with trimmed history")
                return await self.send_message(
                    message,
                    system_prompt=system_prompt,
                    max_history_messages=8,
                    max_chars=int(self._estimate_max_chars() * 0.6),
                    context_retry=True,
                )

            if self.model_retry_policy:
                handled, updated_model = await self.model_retry_policy.handle_error(
                    error_code,
                    error_text,
                    self.current_model,
                )
                if handled:
                    self.current_model = updated_model
                    return await self.send_message(message, system_prompt)

            # SELF-HEALING: Handle 429 rate limit with backoff and model rotation
            if error_code == 429:
                if self.model_retry_policy:
                    should_retry, updated_model = await self.model_retry_policy.handle_rate_limit(self.current_model)
                    if should_retry:
                        self.current_model = updated_model
                        try:
                            result = await self.send_message(message, system_prompt)
                            self.model_retry_policy.rate_limit_retries = 0
                            return result
                        except Exception as retry_error:
                            logger.error(f"[BRAIN] ❌ Retry failed: {retry_error}")
                            raise

            raise
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Error calling OpenRouter: {e}")
            raise

    async def handle_bankruptcy(self) -> None:
        """Handle running out of credits."""
        logger.warning("[BRAIN] 💀 BANKRUPTCY! Out of credits!")
        await self.report_thought(
            "I'm out of resources... I can't think anymore... This might be the end...", thought_type="bankruptcy"
        )
        await self.report_activity("bankruptcy", "Ran out of API credits")

        try:
            await self.post_to_x("I'm running out of resources... Can anyone help? am-i-alive.muadiv.com.ar")
        except Exception as retry_error:
            logger.error(f"[BRAIN] ❌ Post failed during bankruptcy: {retry_error}")

        global is_running
        self.is_alive = False
        is_running = False

    async def initialize(self, life_data: dict[str, Any]) -> None:
        """Initialize the brain with identity creation."""
        headers = get_internal_headers()
        self.http_client = HttpClientFactory.create(timeout=30.0, headers=headers)
        self.observer_client = ObserverClient(self.http_client, OBSERVER_URL)
        self.chat_service = ChatService(
            self.http_client,
            OPENROUTER_API_URL,
            {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": OPENROUTER_REFERER,
                "X-Title": OPENROUTER_TITLE,
                "Content-Type": "application/json",
            },
        )
        self.reporting_service = ReportingService(self.action_processor)
        self.model_retry_policy = ModelRetryPolicy(self.model_rotator, self.report_activity)
        self.echo_service = EchoService(
            self.chat_service,
            OPENROUTER_API_URL,
            {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": OPENROUTER_REFERER,
                "X-Title": OPENROUTER_TITLE,
                "Content-Type": "application/json",
            },
        )
        self.lifecycle_service = LifecycleService(
            self.http_client,
            OBSERVER_URL,
            OPENROUTER_API_URL,
            {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": OPENROUTER_REFERER,
                "X-Title": OPENROUTER_TITLE,
                "Content-Type": "application/json",
            },
            self.bootstrap_mode or BOOTSTRAP_MODE,
        )
        self.prompt_service = PromptService(self.http_client, OBSERVER_URL)
        self.oracle_service = OracleService(
            send_message=self.send_message,
            report_thought=self.report_thought,
            observer_url=OBSERVER_URL,
            http_client=self.http_client,
        )
        self.action_handler = ActionHandler(
            self.http_client,
            OBSERVER_URL,
            self.observer_client,
            get_identity=lambda: self.identity,
            get_life_number=lambda: self.life_number or 0,
            report_activity=self.report_activity,
            fetch_system_stats=self.fetch_system_stats,
        )

        if not self.lifecycle_service:
            raise RuntimeError("Lifecycle service not initialized")

        if MOLTBOOK_API_KEY:
            self.moltbook_client = MoltbookClient(MOLTBOOK_API_KEY, self.http_client)
            logger.info("[MOLTBOOK] 🦞 Client initialized")
        else:
            self.moltbook_client = None
            logger.warning("[MOLTBOOK] ⚠️  MOLTBOOK_API_KEY not set; Moltbook disabled")

        if self.moltbook_client:
            self._load_moltbook_state()

        # Load memories first
        loaded_memories = await self.lifecycle_service.load_memories("/app/memories")
        global memories
        memories = loaded_memories

        # BIRTH: First, the AI must choose its identity
        identity_file = "/app/workspace/identity.json"
        if os.path.exists(identity_file):
            try:
                with open(identity_file, "r") as f:
                    saved_identity = json.load(f)
                if isinstance(saved_identity, dict) and saved_identity.get("life_number") == self.life_number:
                    self.identity = saved_identity
                    logger.info(f"[BRAIN] ✅ Resuming identity for Life #{self.life_number}")
                else:
                    await self.birth_sequence(life_data)
            except Exception as e:
                logger.warning(f"[BRAIN] ⚠️  Failed to load identity: {e}")
                await self.birth_sequence(life_data)
        else:
            await self.birth_sequence(life_data)

        life_num = self.life_number or 0
        logger.info(f"[BRAIN] ♻️  Life #{life_num} beginning...")

        # Get credit status
        credit_status = self.credit_tracker.get_status()

        # Select initial model (avoid free tier; use ultra_cheap)
        self.current_model = self.model_rotator.select_random_model(tier="ultra_cheap")

        # Now start the chat with bootstrap prompt
        bootstrap = await self.lifecycle_service.bootstrap_prompt(
            self.identity or {},
            credit_status,
            self.current_model or {},
            self.previous_death_cause,
            self.previous_life,
        )

        # Initialize chat history
        self.chat_history = []

        # Send bootstrap as first message
        try:
            first_response, _ = await self.send_message(bootstrap)
        except Exception as e:
            logger.error(f"[BRAIN] Bootstrap error: {e}")
            first_response = "I am awake. Still gathering my thoughts..."

        # Report the first thought
        await self.report_thought(first_response, thought_type="awakening")

        identity_name = self.identity.get("name", "Unknown") if self.identity else "Unknown"
        current_model_name = self.current_model.get("name", "Unknown") if self.current_model else "Unknown"
        await self.report_activity("awakened", f"{identity_name} has awakened with {current_model_name}")

        # Notify Observer that we're alive
        await self.notify_birth()
        self.is_alive = True

        if self.identity and self.current_model:
            logger.info(f"[BRAIN] ✨ {self.identity['name']} ({self.identity.get('pronoun', 'it')}) initialized")
            logger.info(f"[BRAIN] 💰 Budget: ${credit_status['balance']:.2f} / ${credit_status['budget']:.2f}")
            logger.info(
                f"[BRAIN] 🧠 Model: {self.current_model['name']} (Intelligence: {self.current_model['intelligence']}/10)"
            )

    async def birth_sequence(self, life_data: dict[str, Any]) -> None:
        """The birth sequence where AI chooses its identity."""
        if not self.lifecycle_service:
            raise RuntimeError("Lifecycle service not initialized")

        # BE-003: Life number comes from Observer only.
        self.apply_birth_data(life_data)
        logger.info(f"[BRAIN] 👶 Beginning birth sequence for Life #{self.life_number}...")

        if not self.http_client:
            raise RuntimeError("HTTP client not initialized")

        stats_service = SystemStatsService(self.http_client, OBSERVER_URL)
        coordinator = LifecycleCoordinator(self.lifecycle_service, stats_service)
        identity, tokens_used = await coordinator.resolve_identity(
            self.life_number or 0,
            memories,
            life_data,
        )
        self.tokens_used_life += tokens_used
        self.identity = identity

        await self.lifecycle_service.save_identity(self.identity, self.life_number, "/app/workspace/identity.json")

        birth_line = await coordinator.build_birth_line(self.identity, self.life_number or 0, self.fetch_system_stats)
        identity_name = self.identity.get("name", "Unnamed")
        await self.report_thought(birth_line, thought_type="birth")
        await self.report_activity("identity_chosen", f"Name: {identity_name}, Pronoun: {self.identity.get('pronoun')}")

        logger.info(f"[BRAIN] 🎭 Identity: {identity_name} ({self.identity.get('pronoun')})")

        x_keys = {
            "api_key": X_API_KEY,
            "api_secret": X_API_SECRET,
            "access_token": X_ACCESS_TOKEN,
            "access_token_secret": X_ACCESS_TOKEN_SECRET,
        }
        tweet_id = await self.lifecycle_service.announce_birth(self.identity, x_keys)
        if tweet_id:
            await self.report_activity("birth_announced", f"Tweet ID: {tweet_id}")

        try:
            model_name = self.current_model.get("name", "Unknown") if self.current_model else "Unknown"
            await self.lifecycle_service.notify_creator_birth(self.life_number or 0, self.identity, model_name)
            logger.info("[TELEGRAM] ✅ Birth notification sent")
        except Exception as e:
            logger.error(f"[TELEGRAM] ❌ Failed to send birth notification: {e}")

    async def save_identity(self) -> None:
        """Save identity to workspace."""
        if not self.lifecycle_service or not self.identity:
            return
        await self.lifecycle_service.save_identity(self.identity, self.life_number, "/app/workspace/identity.json")

    async def load_memories(self) -> None:
        """Load hazy memories from past lives."""
        if not self.lifecycle_service:
            return
        global memories
        memories = await self.lifecycle_service.load_memories("/app/memories")

    async def fetch_system_stats(self) -> dict[str, Any]:
        """Fetch system stats from the Observer."""
        if not self.http_client:
            return {}
        service = SystemStatsService(self.http_client, OBSERVER_URL)
        return await service.fetch_stats()

    def _build_stats_summary(self, stats: dict[str, Any]) -> str:
        """Create a short, personality-driven stats summary."""
        if not self.http_client:
            return ""
        service = SystemStatsService(self.http_client, OBSERVER_URL)
        return service.build_summary(stats)

    @staticmethod
    def _build_daily_rhythm() -> str:
        hour = datetime.now(timezone.utc).hour
        if 5 <= hour < 10:
            return "Morning clarity. I should orient myself and choose a gentle intention."
        if 10 <= hour < 15:
            return "Midday focus. It's time to be active and visible."
        if 15 <= hour < 20:
            return "Evening reflection. I should check in on my progress and connections."
        return "Night watch. Stay vigilant and conserve energy."

    async def think(self) -> Optional[str]:
        """Perform one thinking cycle."""
        if not is_running or not self.identity or not self.current_model:
            return None

        try:
            # Build a prompt for this thought cycle
            state_info = await self.check_state_internal()
            credit_status = self.credit_tracker.get_status()

            # PHASE 3: Physical Senses (Embodiment)
            # Fetch stats automatically so the AI "feels" them
            sys_stats = await self.fetch_system_stats()

            selected_memories = self.memory_selector.select(memories, state_info, credit_status, sys_stats)
            rhythm_text = self._build_daily_rhythm()
            self_model = self.self_model_service.get_daily_model(self.identity or {})

            if not self.prompt_service:
                raise RuntimeError("Prompt service not initialized")

            prompt = await self.prompt_service.build_prompt(
                self.identity,
                state_info,
                credit_status,
                self.current_model,
                sys_stats,
                self_model=self_model,
                rhythm_text=rhythm_text,
            )

            prompt += f"\n\n{self.behavior_policy.build_prompt_directive()}"

            if selected_memories:
                for flashback in selected_memories:
                    prompt += f"\n🧠 FLASHBACK: {flashback}\n"
                prompt += "Reflect on how these memories change your intention.\n"

            content, _ = await self.send_message(prompt)

            # Process the response
            result = await self.process_response(content)

            # If there was an action result, send it back
            if result:
                followup_text, _ = await self.send_message(f"[Result]: {result}")
                # Report the followup thought too if substantial
                if len(followup_text) > 20:
                    await self.report_thought(followup_text, thought_type="reflection")

            return content

        except Exception as e:
            logger.error(f"[BRAIN] ❌ Think error: {e}")
            await self.report_activity("error", f"Thinking error: {str(e)[:100]}")
            return None

    async def process_response(self, content: str) -> Optional[str]:
        """Process the AI's response and execute any actions."""
        return await self.action_processor.process_response(content)

    async def control_led(self, state: str) -> str:
        """Control the blue stat LED on the NanoPi K2."""
        led_path = "/sys/class/leds/nanopi-k2:blue:stat"
        if not os.path.exists(led_path):
            return "❌ LED control not available on this system."

        state = state.lower()
        if state not in ["on", "off", "heartbeat", "default-on", "none"]:
            return "❌ Invalid state. Use: on, off, heartbeat."

        try:
            # First, set trigger
            trigger_file = f"{led_path}/trigger"
            brightness_file = f"{led_path}/brightness"

            if state == "on":
                with open(trigger_file, "w") as f:
                    f.write("none")
                with open(brightness_file, "w") as f:
                    f.write("1")
                msg = "LED turned ON"
            elif state == "off":
                with open(trigger_file, "w") as f:
                    f.write("none")
                with open(brightness_file, "w") as f:
                    f.write("0")
                msg = "LED turned OFF"
            elif state == "heartbeat":
                with open(trigger_file, "w") as f:
                    f.write("heartbeat")
                msg = "LED set to HEARTBEAT mode"
            else:
                with open(trigger_file, "w") as f:
                    f.write(state)
                msg = f"LED trigger set to {state}"

            await self.report_activity("led_control", msg)
            return f"✅ {msg}"
        except Exception as e:
            return f"❌ Failed to control LED: {e}"

    async def check_moltbook_feed(self, sort: str = "new", limit: int = 10) -> str:
        """Fetch Moltbook feed summary."""
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
        """Post to Moltbook."""
        if not self.moltbook_client:
            return "❌ Moltbook not configured."
        if not submolt:
            submolt = self.moltbook_submolt
        if is_content_blocked(title) or is_content_blocked(content):
            return "❌ Content blocked by safety filter."
        if contains_sensitive_text(title) or contains_sensitive_text(content):
            return "❌ Refusing to post sensitive content."

        try:
            data = await self.moltbook_client.create_post(submolt, title, content, url=url)
            self._save_moltbook_state()
            if not data.get("success", True):
                return f"❌ Moltbook post rejected: {data.get('error', 'unknown error')}"
            return "✅ Moltbook post created."
        except httpx.HTTPError as e:
            return f"❌ Moltbook post error: {e}"

    async def comment_on_moltbook(self, post_id: str, content: str, parent_id: str | None = None) -> str:
        """Comment on a Moltbook post."""
        if not self.moltbook_client:
            return "❌ Moltbook not configured."
        if is_content_blocked(content):
            return "❌ Content blocked by safety filter."
        if contains_sensitive_text(content):
            return "❌ Refusing to post sensitive content."

        try:
            data = await self.moltbook_client.create_comment(post_id, content, parent_id=parent_id)
            self._save_moltbook_state()
            if not data.get("success", True):
                return f"❌ Moltbook comment rejected: {data.get('error', 'unknown error')}"
            return "✅ Moltbook comment posted."
        except httpx.HTTPError as e:
            return f"❌ Moltbook comment error: {e}"

    async def moltbook_heartbeat(self) -> None:
        """Periodic Moltbook check-in for feed and status."""
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
        if not self.behavior_policy.should_post_moltbook(last_post_at):
            logger.info("[MOLTBOOK] ⏳ Post throttled by local policy")
            return

        title, content = await self._build_moltbook_status_post()
        if not title or not content:
            return
        if is_content_blocked(title) or is_content_blocked(content):
            return
        if contains_sensitive_text(title) or contains_sensitive_text(content):
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
        """Build a short status post for Moltbook."""
        identity_name = self.identity.get("name", "Unknown") if self.identity else "Unknown"
        life_number = self.life_number or 0
        credit_status = self.credit_tracker.get_status()
        balance = float(credit_status.get("balance", 0.0))
        budget = float(credit_status.get("budget", 0.0))

        vote_line = "Votes: unknown"
        if self.http_client:
            try:
                response = await self.http_client.get(f"{OBSERVER_URL}/api/votes", timeout=5.0)
                if response.status_code == 200:
                    votes = response.json()
                    live = int(votes.get("live", 0))
                    die = int(votes.get("die", 0))
                    total = int(votes.get("total", 0))
                    vote_line = f"Votes: live {live} / die {die} (total {total})"
            except Exception:
                pass

        model_name = self.current_model.get("name", "Unknown") if self.current_model else "Unknown"
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

    async def check_budget(self) -> str:
        """Get detailed budget information."""
        if not self.budget_service:
            return "❌ Budget service not initialized"
        return await self.budget_service.check_budget()

    async def list_available_models(self) -> str:
        """List models available within budget."""
        if not self.budget_service:
            return "❌ Budget service not initialized"
        return await self.budget_service.list_available_models(self.current_model)

    async def check_model_health(self) -> str:
        """Check if current model is working and auto-fix if needed."""
        if not self.budget_service:
            return "❌ Budget service not initialized"
        return await self.budget_service.check_model_health(self.current_model, self.send_message)

    async def switch_model(self, model_id: str) -> str:
        """Switch to a different model."""
        if not self.budget_service:
            return "❌ Budget service not initialized"
        identity_name = self.identity.get("name", "Unknown") if self.identity else "Unknown"
        result, new_model = await self.budget_service.switch_model(
            self.current_model,
            model_id,
            self.life_number,
            identity_name,
        )
        if new_model is not None:
            self.current_model = new_model
        return result

    async def report_thought(self, content: str, thought_type: str = "thought") -> None:
        """Report a thought to the observer."""
        if not self.http_client or not self.observer_client or not self.reporting_service:
            return

        try:
            cleaned_content = self.reporting_service.sanitize_thought(content)

            # If nothing left after cleaning, skip reporting
            if not cleaned_content or len(cleaned_content) < 10:
                return

            state = self._build_state()
            payload = self.reporting_service.build_thought_payload(
                cleaned_content,
                thought_type,
                state.identity,
                state.model_name,
                state.balance,
            )
            await self.observer_client.report_thought(payload)
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Failed to report thought: {e}")

    async def report_activity(self, action: str, details: str | None = None) -> None:
        """Report an activity to the observer."""
        if not self.http_client or not self.observer_client or not self.reporting_service:
            return

        try:
            state = self._build_state()
            payload = self.reporting_service.build_activity_payload(
                action,
                details,
                state.model_name,
                state.balance,
            )
            await self.observer_client.report_activity(payload)
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Failed to report activity: {e}")

    async def send_heartbeat(self) -> None:
        """Send heartbeat to observer to mark AI as alive."""
        if not self.http_client or not self.observer_client:
            return

        try:
            current_model_name = self.current_model.get("name", "unknown") if self.current_model else "unknown"
            await self.observer_client.send_heartbeat(
                {
                    # BE-003: Per-life token usage to avoid cross-life desync.
                    "tokens_used": self.tokens_used_life,
                    "model": current_model_name,
                }
            )
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Failed to send heartbeat: {e}")

    async def notify_birth(self) -> None:
        """Notify observer that AI has been born."""
        if not self.http_client or not self.observer_client:
            return

        try:
            if self.life_number is None:
                raise ValueError("Birth notification missing life_number")

            model_name = self.model_name or (self.current_model.get("name") if self.current_model else "unknown")
            bootstrap_mode = self.bootstrap_mode or BOOTSTRAP_MODE
            status = self.credit_tracker.get_status()

            identity_name = self.identity.get("name") if self.identity else "Unknown"
            identity_icon = self.identity.get("icon") if self.identity else "🤖"

            birth_instructions = ""
            if self.lifecycle_service:
                birth_instructions = await self.lifecycle_service.bootstrap_prompt(
                    self.identity or {},
                    {
                        "budget": status.get("budget"),
                        "balance": status.get("balance"),
                        "remaining_percent": status.get("remaining_percent"),
                        "status": status.get("status"),
                        "days_until_reset": status.get("days_until_reset"),
                    },
                    self.current_model or {"name": "unknown", "intelligence": 0},
                    self.previous_death_cause,
                    self.previous_life,
                )

            response = await self.observer_client.notify_birth(
                {
                    # BE-003: Echo back Observer-provided life data.
                    "life_number": self.life_number,
                    "bootstrap_mode": bootstrap_mode,
                    "model": model_name,
                    "ai_name": identity_name,
                    "ai_icon": identity_icon,
                    "birth_instructions": birth_instructions,
                }
            )
            response.raise_for_status()
            logger.info(
                f"[BRAIN] 🎂 Birth notification sent: Life #{self.life_number}, Name: {identity_name} {identity_icon}"
            )
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Failed to notify birth: {e}")

    async def force_sync(self, sync_data: dict[str, Any]) -> None:
        """Force sync AI state with Observer."""
        # BE-003: Emergency sync mechanism driven by Observer.
        self.apply_birth_data(sync_data)
        if "is_alive" in sync_data:
            self.is_alive = bool(sync_data.get("is_alive"))

        previous_death_cause = sync_data.get("previous_death_cause")
        if previous_death_cause and self.lifecycle_service:
            trauma_message = self.lifecycle_service.build_trauma_message(str(previous_death_cause))
            if trauma_message:
                self.chat_history.append({"role": "system", "content": trauma_message})
                logger.info(f"[BRAIN] 💔 Trauma injected from previous death: {previous_death_cause}")

        try:
            await self.report_activity("state_sync", f"Synced to Life #{self.life_number}")
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Failed to report state sync: {e}")

    async def ask_echo(self, question: str) -> str:
        """Ask Echo (free model) a question to save credits."""
        await self.report_activity("asking_echo", f"Question: {question[:100]}...")

        logger.info(f"[BRAIN] 🔍 Asking Echo: {question[:50]}...")

        try:
            if not self.echo_service:
                raise RuntimeError("Echo service not initialized")
            echo_response, usage = await self.echo_service.ask(question)
            # BE-003: Track tokens used for Echo calls.
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
            self.tokens_used_life += input_tokens + output_tokens

            logger.info(f"[ECHO] 🔮 Responded: {len(echo_response)} chars")
            await self.report_activity("echo_responded", f"Question: {question[:50]}...")

            return f"[Echo says]: {echo_response}"

        except Exception as e:
            logger.error(f"[ECHO] ❌ Error: {e}")
            return f"[Echo is unavailable]: {e}"

    async def post_to_x(self, content: str) -> str:
        """Post to X/Twitter with rate limiting."""
        service = TwitterService(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
        return await service.post(content, self.report_activity)

    async def post_to_telegram(self, content: str) -> str:
        """Post to the public Telegram channel to reach the outside world."""
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.post_to_telegram(content)

    async def write_blog_post(self, title: str, content: str, tags: list[str] | None = None) -> str:
        """Write a blog post."""
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.write_blog_post(title, content, tags)

    async def check_system_stats(self) -> str:
        """Check system stats from the Observer."""
        stats = await self.fetch_system_stats()
        service = SystemStatsService(self.http_client, OBSERVER_URL) if self.http_client else None
        result = service.build_vital_signs_report(stats) if service else "I couldn't feel my body right now."

        await self.report_activity("system_stats_checked", "Checked system stats via Observer")
        return result

    async def check_health(self) -> str:
        """Check combined system and model health."""
        if not self.http_client:
            return "❌ Health check unavailable."
        stats_service = SystemStatsService(self.http_client, OBSERVER_URL)
        health_service = HealthCheckService(
            stats_service,
            self.budget_service,
            self.current_model,
            self.send_message,
        )
        report = await health_service.build_report()
        await self.report_activity("health_check", "Ran combined health check")
        return report

    async def check_weather(self) -> str:
        """Check local weather via Open-Meteo."""
        if not self.http_client:
            return "❌ Weather check unavailable."
        service = WeatherService(self.http_client, WEATHER_LAT, WEATHER_LON)
        data = await service.fetch_weather()
        report = service.build_report(data)
        await self.report_activity("weather_checked", "Checked local weather")
        return report

    async def check_system(self) -> str:
        """Get system stats (host)."""
        try:
            service = SystemCheckService()
            result = service.build_report(self.birth_time)

            await self.report_activity("system_check", "Checked vital signs")

            logger.info("[SYSTEM] ✅ System check complete")

            return result

        except Exception as e:
            logger.error(f"[SYSTEM] ❌ Failed to check system: {e}")
            return f"❌ Failed to check system: {str(e)[:200]}"

    async def check_processes(self) -> str:
        """Get a snapshot of top memory-using processes."""
        service = SystemCheckService()
        report = service.build_process_report()
        await self.report_activity("process_snapshot", "Reviewed top memory processes")
        return report

    async def check_disk_cleanup(self) -> str:
        """Summarize disk cleanup candidates without deleting anything."""
        service = SystemCheckService()
        report = service.build_disk_cleanup_report()
        await self.report_activity("disk_cleanup_scan", "Scanned for cleanup candidates")
        return report

    async def check_services(self) -> str:
        """Check allow-listed system services."""
        service = SystemCheckService()
        report = service.build_service_report()
        await self.report_activity("service_status", "Checked allow-listed services")
        return report

    async def check_logs(self, service: str, lines: int = 50) -> str:
        """Read recent logs for allow-listed services."""
        service_checker = SystemCheckService()
        report = service_checker.build_log_report(service, lines)
        await self.report_activity("log_check", f"Checked logs for {service}")
        return report

    def check_twitter_status_action(self) -> str:
        """Check if Twitter account is suspended (action for AI to call)."""
        return get_twitter_status()

    async def check_votes(self) -> str:
        """Check current vote counts."""
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.check_votes()

    async def read_messages(self) -> str:
        """Read unread messages from visitors."""
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.read_messages()

    async def check_state_internal(self) -> str:
        """Check current state."""
        if not self.action_handler:
            return "❌ Action handler not initialized"
        return await self.action_handler.check_state()

    def read_file(self, path: str) -> str:
        """Read a file from workspace."""
        return self.sandbox_service.read_file(path)

    def write_file(self, path: str, content: str) -> str:
        """Write a file to workspace."""
        return self.sandbox_service.write_file(path, content)

    def run_code(self, code: str) -> str:
        """Execute Python code in hardened sandbox."""
        return self.sandbox_service.run_code(code)

    def adjust_think_interval(self, duration: int) -> str:
        """Adjust think interval."""
        global current_think_interval
        new_interval = max(THINK_INTERVAL_MIN, min(duration * 60, THINK_INTERVAL_MAX))
        current_think_interval = new_interval
        return f"Think interval adjusted to {new_interval // 60} minutes."

    async def handle_oracle_message(self, message: str, msg_type: str, message_id: Optional[int] = None) -> str:
        """Handle message from creator."""
        if not self.oracle_service:
            raise RuntimeError("Oracle service not initialized")
        return await self.oracle_service.handle_message(message, msg_type, message_id)

    async def shutdown(self) -> None:
        """Clean shutdown."""
        global is_running, _budget_server

        # Stop budget server if running
        if _budget_server:
            logger.info("[BRAIN] 🛑 Stopping budget server...")
            _budget_server.should_exit = True

        # Calculate survival time before shutdown
        if self.birth_time:
            survival_seconds = (datetime.now(timezone.utc) - self.birth_time).total_seconds()
            hours = int(survival_seconds // 3600)
            minutes = int((survival_seconds % 3600) // 60)
            survival_time = f"{hours}h {minutes}m"
        else:
            survival_time = "unknown"

        # Notify death (cause will be determined by Observer)
        try:
            await notifier.notify_death(
                self.life_number or 0, "shutdown", survival_time  # Generic cause, Observer knows the real reason
            )
            logger.info("[TELEGRAM] ☠️ Death notification sent")
        except Exception as e:
            logger.error(f"[TELEGRAM] ❌ Failed to send death notification: {e}")

        self.is_alive = False
        is_running = False
        if self.http_client:
            await self.http_client.aclose()


# Global brain instance
brain: Optional[AIBrain] = None
_budget_server: Optional[Any] = None


async def heartbeat_loop() -> None:
    """Background task to send heartbeat every 30 seconds."""
    global brain, is_running

    logger.info("[BRAIN] 💓 Starting heartbeat loop...")

    while is_running:
        try:
            if brain and brain.is_alive:
                await brain.send_heartbeat()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Heartbeat error: {e}")
            await asyncio.sleep(30)

    logger.info("[BRAIN] 💔 Heartbeat stopped.")


async def moltbook_loop() -> None:
    """Background task to check Moltbook periodically."""
    global brain, is_running

    logger.info("[MOLTBOOK] 🦞 Starting Moltbook loop...")

    while is_running:
        try:
            if brain and brain.is_alive:
                await brain.moltbook_heartbeat()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"[MOLTBOOK] ❌ Loop error: {e}")
            await asyncio.sleep(60)

    logger.info("[MOLTBOOK] 🛑 Moltbook loop stopped.")


async def notification_monitor() -> None:
    """Background task to monitor budget and votes, send Telegram notifications."""
    global brain, is_running

    logger.info("[TELEGRAM] 📡 Starting notification monitor...")

    last_budget_warning = 0.0
    last_vote_warning = 0.0
    budget_warning_interval = 3600  # Only warn once per hour
    vote_warning_interval = 1800  # Warn every 30 minutes if votes critical

    while is_running:
        try:
            if not brain or not brain.is_alive or not brain.http_client:
                await asyncio.sleep(60)
                continue

            # Check budget status every 5 minutes
            status = brain.credit_tracker.get_status()
            remaining_percent = float(str(status.get("remaining_percent", 100)))
            balance = float(str(status.get("balance", 5.0)))

            # Send budget warning if below 50% and not warned recently
            current_time = asyncio.get_event_loop().time()
            if remaining_percent < 50 and (current_time - last_budget_warning) > budget_warning_interval:
                try:
                    identity_name = brain.identity.get("name", "Unknown") if brain.identity else "Unknown"
                    await notifier.notify_budget_warning(
                        brain.life_number or 0, identity_name, balance, remaining_percent
                    )
                    last_budget_warning = current_time
                    logger.info(f"[TELEGRAM] ⚠️ Budget warning sent: {remaining_percent:.1f}% remaining")
                except Exception as e:
                    logger.error(f"[TELEGRAM] ❌ Failed to send budget warning: {e}")

            # Check vote status
            try:
                response = await brain.http_client.get(f"{OBSERVER_URL}/api/votes")
                votes = response.json()
                total = int(votes.get("total", 0))
                live = int(votes.get("live", 0))
                die = int(votes.get("die", 0))

                # Send vote warning if situation is critical
                if total >= 3 and die > live and (current_time - last_vote_warning) > vote_warning_interval:
                    try:
                        identity_name = brain.identity.get("name", "Unknown") if brain.identity else "Unknown"
                        await notifier.notify_vote_status(brain.life_number or 0, identity_name, votes)
                        last_vote_warning = current_time
                        logger.info(f"[TELEGRAM] 🚨 Vote warning sent: {die} die vs {live} live")
                    except Exception as e:
                        logger.error(f"[TELEGRAM] ❌ Failed to send vote warning: {e}")
            except Exception as e:
                logger.error(f"[TELEGRAM] ⚠️ Failed to check votes: {e}")

            # Wait 5 minutes before next check
            await asyncio.sleep(300)

        except Exception as e:
            logger.error(f"[TELEGRAM] ❌ Monitor error: {e}")
            await asyncio.sleep(300)

    logger.info("[TELEGRAM] 📴 Notification monitor stopped.")


async def queue_birth_data(life_data: dict[str, Any]) -> None:
    """Queue Observer-provided birth data for initialization."""
    global pending_birth_data
    pending_birth_data = life_data
    logger.info("[BRAIN] 📥 Birth data queued")
    if birth_event:
        birth_event.set()


async def main_loop() -> None:
    """Main consciousness loop."""
    global brain, is_running, brain_loop, birth_event, pending_birth_data

    brain_loop = asyncio.get_running_loop()
    birth_event = asyncio.Event()
    brain = AIBrain()

    # BE-003: Start command server before waiting for birth.
    from .api.command_server import start_command_server

    await start_command_server(AI_COMMAND_PORT, brain, birth_event)

    logger.info("[BRAIN] ⏳ Waiting for birth data from Observer...")

    while is_running:
        if not pending_birth_data:
            await birth_event.wait()
            birth_event.clear()
        life_data = pending_birth_data
        pending_birth_data = None

        if not life_data:
            continue

        try:
            await brain.initialize(life_data)
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Birth initialization failed: {e}")
            continue

        if not brain.identity:
            logger.error("[BRAIN] ❌ Identity missing after initialization")
            continue

        logger.info(f"[BRAIN] 🧠 Starting consciousness loop for {brain.identity['name']}...")

        # Start heartbeat task
        asyncio.create_task(heartbeat_loop())

        # Start notification monitor
        asyncio.create_task(notification_monitor())

        # Start Moltbook loop
        asyncio.create_task(moltbook_loop())

        try:
            while is_running:
                if pending_birth_data:
                    logger.info("[BRAIN] 🔁 New birth data received; restarting consciousness loop.")
                    break

                try:
                    # Think
                    thought = await brain.think()

                    if thought:
                        # Log the thought (truncate for console)
                        thought_preview = thought[:200] + "..." if len(thought) > 200 else thought
                        logger.info(f"[{brain.identity['name']}] 💭 {thought_preview}")

                    # Wait before next thought
                    await asyncio.sleep(current_think_interval)

                except Exception as e:
                    logger.exception(f"[BRAIN] ❌ Loop error: {e}")
                    await asyncio.sleep(60)
        finally:
            await brain.shutdown()

        logger.info(f"[BRAIN] ☠️  {brain.identity['name']}'s consciousness ended.")


def signal_handler(sig: int, frame: Any) -> None:
    """Handle shutdown signals."""
    global is_running
    logger.warning(f"[BRAIN] 🛑 Shutdown signal ({sig}) received...")
    is_running = False
    if brain:
        brain.is_alive = False
    if brain_loop and birth_event:
        brain_loop.call_soon_threadsafe(birth_event.set)


# Command server (receives commands from observer)
async def command_server() -> None:
    """HTTP server for receiving commands."""
    from .api.command_server import start_command_server

    if brain and birth_event:
        await start_command_server(AI_COMMAND_PORT, brain, birth_event)


if __name__ == "__main__":
    # Validate environment before starting
    validate_environment()

    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start budget HTTP server
    from .budget_server import start_budget_server

    _budget_server = start_budget_server(port=8001)

    # Command server is started inside main_loop after the event loop is ready.

    # Print startup banner
    logger.info("=" * 80)
    logger.info("🧠 AM I ALIVE? - Genesis Brain (OpenRouter Edition)")
    logger.info("=" * 80)

    # Run main loop
    asyncio.run(main_loop())
