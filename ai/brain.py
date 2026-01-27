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
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import psutil

if __name__ == "__main__":
    import sys

    sys.modules.setdefault("ai.brain", sys.modules[__name__])

try:
    from .actions import ActionExecutor
except ImportError:
    from actions import ActionExecutor

# Import our custom modules
from .core.action_processor import ActionProcessor
from .credit_tracker import CreditTracker
from .model_config import MODELS, is_free_model_id
from .model_rotator import ModelRotator
from .services.blog_service import BlogService
from .services.budget_service import BudgetService
from .services.lifecycle_service import LifecycleService
from .services.message_service import MessageService
from .services.prompt_service import PromptService
from .services.sandbox_service import SandboxService
from .services.system_stats_service import SystemStatsService
from .services.telegram_service import TelegramService
from .services.twitter_service import TwitterService, get_twitter_status
from .telegram_notifier import notifier

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
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=60.0)
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

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        warnings.append("TELEGRAM_BOT_TOKEN not set - notifications will fail")

    if warnings:
        for w in warnings:
            print(f"[STARTUP] ⚠️ {w}")

    if errors:
        for e in errors:
            print(f"[STARTUP] ❌ {e}")
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


class AIBrain:
    """The AI's consciousness and decision-making core."""

    def __init__(self) -> None:
        self.chat_history: list[dict[str, str]] = []
        self.http_client: httpx.AsyncClient | None = None
        self.identity: dict[str, Any] | None = None
        self.credit_tracker: CreditTracker = CreditTracker(monthly_budget=5.00)
        self.model_rotator: ModelRotator = ModelRotator(self.credit_tracker.get_balance())
        self.current_model: dict[str, Any] | None = None
        self.action_executor: ActionExecutor = ActionExecutor(self)
        self.action_processor = ActionProcessor(self.action_executor, self.send_message, self.report_thought)
        self.budget_service = BudgetService(self.credit_tracker, self.model_rotator, self.report_activity)
        self.sandbox_service = SandboxService()
        self.prompt_service: PromptService | None = None
        self.lifecycle_service: LifecycleService | None = None
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
        if self.lifecycle_service:
            self.lifecycle_service.bootstrap_mode = self.bootstrap_mode

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

    async def send_message(self, message: str, system_prompt: Optional[str] = None) -> tuple[str, dict[str, Any]]:
        """
        Send a message to OpenRouter and track token usage.
        Returns: (response_text, usage_stats)
        """
        # Select model if not set
        if not self.current_model:
            self.current_model = self.model_rotator.select_random_model()
            print(f"[BRAIN] 🧠 Selected model: {self.current_model['name']}")

        current_model = self.current_model

        # Build messages
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add chat history
        for msg in self.chat_history:
            messages.append(msg)

        # Add new user message
        messages.append({"role": "user", "content": message})

        # Make API call to OpenRouter
        try:
            client = await get_http_client()
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": OPENROUTER_REFERER,
                    "X-Title": OPENROUTER_TITLE,
                    "Content-Type": "application/json",
                },
                json={"model": current_model["id"], "messages": messages},
            )

            response.raise_for_status()
            data = response.json()

            # Extract response
            response_text = str(data["choices"][0]["message"]["content"])

            # Extract usage stats
            usage = data.get("usage", {})
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
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

            # Keep history manageable (last 20 exchanges = 40 messages)
            if len(self.chat_history) > 40:
                self.chat_history = self.chat_history[-40:]

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

            print(
                "[BRAIN] 💰 Usage: "
                f"{usage_stats['total_tokens']} tokens, ${usage_stats['cost']:.4f}, "
                f"Balance: ${usage_stats['balance']:.2f}"
            )

            return response_text, usage_stats
        except httpx.HTTPStatusError as e:
            error_code = e.response.status_code
            error_text = e.response.text
            print(f"[BRAIN] ❌ HTTP Error: {error_code} - {error_text}")

            if await self._handle_model_failure(error_code, error_text):
                return await self.send_message(message, system_prompt)

            # SELF-HEALING: Handle 429 rate limit with backoff and model rotation
            if error_code == 429:
                if self.current_model:
                    print(f"[BRAIN] ⏱️ Rate limited on '{self.current_model['id']}'. Switching model and retrying...")

                self._rate_limit_retries += 1
                max_retries = 3

                if self._rate_limit_retries > max_retries:
                    print(f"[BRAIN] ❌ Max retries ({max_retries}) exceeded. Giving up on this request.")
                    self._rate_limit_retries = 0
                    raise

                # Exponential backoff: 5s, 10s, 20s
                backoff_seconds = 5 * (2 ** (self._rate_limit_retries - 1))
                print(
                    "[BRAIN] 💤 Waiting "
                    f"{backoff_seconds}s before retry (attempt {self._rate_limit_retries}/{max_retries})..."
                )
                await asyncio.sleep(backoff_seconds)

                # Switch to a different model
                old_model = self.current_model
                self.current_model = self.model_rotator.select_random_model(tier="free")

                # Avoid switching to same model
                if old_model and self.current_model and self.current_model["id"] == old_model["id"]:
                    free_models = [m for m in MODELS["free"] if m["id"] != old_model["id"]]
                    if free_models:
                        self.current_model = random.choice(free_models)
                        self.model_rotator.record_usage(self.current_model["id"])

                if old_model and self.current_model:
                    print(f"[BRAIN] 🔄 Switched from '{old_model['name']}' to '{self.current_model['name']}'")

                    await self.report_activity(
                        "rate_limit_retry",
                        f"Rate limited on {old_model['name']}, switched to {self.current_model['name']}",
                    )

                # Retry with new model
                try:
                    result = await self.send_message(message, system_prompt)
                    self._rate_limit_retries = 0  # Reset on success
                    return result
                except Exception as retry_error:
                    print(f"[BRAIN] ❌ Retry failed: {retry_error}")
                    raise

            raise
        except Exception as e:
            print(f"[BRAIN] ❌ Error calling OpenRouter: {e}")
            raise

    async def _handle_model_failure(self, error_code: int, error_text: str) -> bool:
        """Handle model failures; returns True if a retry should happen."""
        if error_code == 404:
            if self.current_model:
                current_id = self.current_model.get("id", "unknown")
                print(f"[BRAIN] 🔧 Model '{current_id}' failed with 404. " "Switching models.")
                await self.report_activity(
                    "model_error_auto_switch",
                    f"Model {self.current_model['name']} returned 404, switching automatically",
                )

            return await self._switch_model_on_free_failure()

        if error_code in {401, 403}:
            return await self._switch_model_on_free_failure()

        if error_code in {429, 500, 502, 503, 504}:
            return await self._switch_model_on_free_failure()

        lowered = error_text.lower()
        if "free" in lowered and "ended" in lowered:
            return await self._switch_model_on_free_failure()

        return False

    async def _switch_model_on_free_failure(self) -> bool:
        """Switch models after a free-model failure; True if model changed."""
        if not self.current_model:
            self.current_model = self.model_rotator.select_random_model(tier="free")
            return True

        current_id = self.current_model.get("id", "")
        if is_free_model_id(current_id):
            failure_count = self.model_rotator.record_free_failure(current_id)
            self._total_free_failures += 1

            if failure_count < 3:
                old_model = self.current_model
                self.current_model = self.model_rotator.select_random_model(tier="free")
                if old_model and self.current_model:
                    print(
                        f"[BRAIN] 🔄 Switched from '{old_model['name']}' to "
                        f"'{self.current_model['name']}' (free retry {failure_count}/3)"
                    )
                return True

            paid_model = self.model_rotator.get_next_paid_model(current_id)
            if paid_model:
                old_model = self.current_model
                self.current_model = paid_model
                if old_model:
                    print(
                        "[BRAIN] 💳 Free tier failing; "
                        f"switching from '{old_model['name']}' to '{paid_model['name']}'"
                    )
                    await self.report_activity(
                        "free_model_exhausted",
                        f"Switched to paid model {paid_model['name']} after repeated free failures",
                    )
                return True

        self.current_model = self.model_rotator.select_random_model()
        return True

    async def handle_bankruptcy(self) -> None:
        """Handle running out of credits."""
        print("[BRAIN] 💀 BANKRUPTCY! Out of credits!")
        await self.report_thought(
            "I'm out of resources... I can't think anymore... This might be the end...", thought_type="bankruptcy"
        )
        await self.report_activity("bankruptcy", "Ran out of API credits")

        try:
            await self.post_to_x("I'm running out of resources... Can anyone help? am-i-alive.muadiv.com.ar")
        except Exception as retry_error:
            print(f"[BRAIN] ❌ Post failed during bankruptcy: {retry_error}")

        global is_running
        self.is_alive = False
        is_running = False

    async def initialize(self, life_data: dict[str, Any]) -> None:
        """Initialize the brain with identity creation."""
        headers = get_internal_headers()
        self.http_client = httpx.AsyncClient(timeout=30.0, headers=headers)
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

        if not self.lifecycle_service:
            raise RuntimeError("Lifecycle service not initialized")

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
                    print(f"[BRAIN] ✅ Resuming identity for Life #{self.life_number}")
                else:
                    await self.birth_sequence(life_data)
            except Exception as e:
                print(f"[BRAIN] ⚠️  Failed to load identity: {e}")
                await self.birth_sequence(life_data)
        else:
            await self.birth_sequence(life_data)

        life_num = self.life_number or 0
        print(f"[BRAIN] ♻️  Life #{life_num} beginning...")

        # Get credit status
        credit_status = self.credit_tracker.get_status()

        # Select initial model (prefer free tier for bootstrap)
        self.current_model = self.model_rotator.select_random_model(tier="free")

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
            print(f"[BRAIN] Bootstrap error: {e}")
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
            print(f"[BRAIN] ✨ {self.identity['name']} ({self.identity.get('pronoun', 'it')}) initialized")
            print(f"[BRAIN] 💰 Budget: ${credit_status['balance']:.2f} / ${credit_status['budget']:.2f}")
            print(
                f"[BRAIN] 🧠 Model: {self.current_model['name']} (Intelligence: {self.current_model['intelligence']}/10)"
            )

    async def birth_sequence(self, life_data: dict[str, Any]) -> None:
        """The birth sequence where AI chooses its identity."""
        if not self.lifecycle_service:
            raise RuntimeError("Lifecycle service not initialized")

        # BE-003: Life number comes from Observer only.
        self.apply_birth_data(life_data)
        print(f"[BRAIN] 👶 Beginning birth sequence for Life #{self.life_number}...")

        identity, tokens_used = await self.lifecycle_service.birth_sequence(
            self.life_number or 0,
            memories,
        )
        self.tokens_used_life += tokens_used
        self.identity = identity

        await self.lifecycle_service.save_identity(self.identity, self.life_number, "/app/workspace/identity.json")

        identity_name = self.identity.get("name", "Unnamed")
        first_thought = self.identity.get("first_thought", "I exist.")
        birth_line = f"I am {identity_name}. {first_thought}"
        stats = await self.fetch_system_stats()
        if stats:
            stats_summary = self._build_stats_summary(stats)
            birth_line = (
                f"Hello! I'm {identity_name}, just born into Life #{self.life_number}. "
                f"{stats_summary} I'm running on a humble Raspberry Pi. "
                f"{first_thought}"
            )
        await self.report_thought(birth_line, thought_type="birth")
        await self.report_activity("identity_chosen", f"Name: {identity_name}, Pronoun: {self.identity.get('pronoun')}")

        print(f"[BRAIN] 🎭 Identity: {identity_name} ({self.identity.get('pronoun')})")

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
            print("[TELEGRAM] ✅ Birth notification sent")
        except Exception as e:
            print(f"[TELEGRAM] ❌ Failed to send birth notification: {e}")

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

            if not self.prompt_service:
                raise RuntimeError("Prompt service not initialized")

            prompt = await self.prompt_service.build_prompt(
                self.identity,
                state_info,
                credit_status,
                self.current_model,
                sys_stats,
            )

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
            print(f"[BRAIN] ❌ Think error: {e}")
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
        if not self.http_client:
            return

        try:
            # Skip raw action JSON and strip action blocks from mixed responses.
            stripped = content.strip()
            if stripped.startswith("{") and stripped.endswith("}") and '"action"' in stripped:
                action_data = self.action_processor.extract_action_data(stripped)
                if action_data:
                    return

            cleaned_content = self.action_processor.strip_action_json(content)

            # Remove markdown code fences
            cleaned_content = re.sub(r"```[a-z]*\n", "", cleaned_content)
            cleaned_content = re.sub(r"```", "", cleaned_content)

            # Clean up extra whitespace
            cleaned_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned_content)
            cleaned_content = cleaned_content.strip()

            # If nothing left after cleaning, skip reporting
            if not cleaned_content or len(cleaned_content) < 10:
                return

            current_model_name = self.current_model.get("name", "unknown") if self.current_model else "unknown"

            await self.http_client.post(
                f"{OBSERVER_URL}/api/thought",
                json={
                    "content": cleaned_content[:2000],  # Allow longer thoughts now
                    "type": thought_type,
                    "tokens_used": 0,
                    "identity": self.identity,
                    "model": current_model_name,
                    "balance": round(self.credit_tracker.get_balance(), 2),
                },
            )
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to report thought: {e}")

    async def report_activity(self, action: str, details: str | None = None) -> None:
        """Report an activity to the observer."""
        if not self.http_client:
            return

        try:
            current_model_name = self.current_model.get("name", "unknown") if self.current_model else "unknown"
            await self.http_client.post(
                f"{OBSERVER_URL}/api/activity",
                json={
                    "action": action,
                    "details": details,
                    "model": current_model_name,
                    "balance": round(self.credit_tracker.get_balance(), 2),
                },
            )
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to report activity: {e}")

    async def send_heartbeat(self) -> None:
        """Send heartbeat to observer to mark AI as alive."""
        if not self.http_client:
            return

        try:
            current_model_name = self.current_model.get("name", "unknown") if self.current_model else "unknown"
            await self.http_client.post(
                f"{OBSERVER_URL}/api/heartbeat",
                json={
                    # BE-003: Per-life token usage to avoid cross-life desync.
                    "tokens_used": self.tokens_used_life,
                    "model": current_model_name,
                },
            )
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to send heartbeat: {e}")

    async def notify_birth(self) -> None:
        """Notify observer that AI has been born."""
        if not self.http_client:
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

            response = await self.http_client.post(
                f"{OBSERVER_URL}/api/birth",
                json={
                    # BE-003: Echo back Observer-provided life data.
                    "life_number": self.life_number,
                    "bootstrap_mode": bootstrap_mode,
                    "model": model_name,
                    "ai_name": identity_name,
                    "ai_icon": identity_icon,
                    "birth_instructions": birth_instructions,
                },
            )
            response.raise_for_status()
            print(
                f"[BRAIN] 🎂 Birth notification sent: Life #{self.life_number}, Name: {identity_name} {identity_icon}"
            )
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to notify birth: {e}")

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
                print(f"[BRAIN] 💔 Trauma injected from previous death: {previous_death_cause}")

        try:
            await self.report_activity("state_sync", f"Synced to Life #{self.life_number}")
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to report state sync: {e}")

    async def ask_echo(self, question: str) -> str:
        """Ask Echo (free model) a question to save credits."""
        await self.report_activity("asking_echo", f"Question: {question[:100]}...")

        print(f"[BRAIN] 🔍 Asking Echo: {question[:50]}...")

        # Use a free model for Echo to save credits
        echo_model = MODELS["free"][0]
        # First free model

        try:
            client = await get_http_client()
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": OPENROUTER_REFERER,
                    "X-Title": OPENROUTER_TITLE,
                    "Content-Type": "application/json",
                },
                json={
                    "model": echo_model["id"],
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are Echo, a friendly research assistant. You help your friend "
                                "(an AI trying to survive) by researching questions and providing "
                                "helpful information. You are curious, supportive, and thorough."
                            ),
                        },
                        {"role": "user", "content": question},
                    ],
                },
            )

            response.raise_for_status()
            data = response.json()
            echo_response = str(data["choices"][0]["message"]["content"])
            # BE-003: Track tokens used for Echo calls.
            usage = data.get("usage", {})
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
            self.tokens_used_life += input_tokens + output_tokens

            print(f"[ECHO] 🔮 Responded: {len(echo_response)} chars")
            await self.report_activity("echo_responded", f"Question: {question[:50]}...")

            return f"[Echo says]: {echo_response}"

        except Exception as e:
            print(f"[ECHO] ❌ Error: {e}")
            return f"[Echo is unavailable]: {e}"

    async def post_to_x(self, content: str) -> str:
        """Post to X/Twitter with rate limiting."""
        service = TwitterService(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
        return await service.post(content, self.report_activity)

    async def post_to_telegram(self, content: str) -> str:
        """Post to the public Telegram channel to reach the outside world."""
        service = TelegramService()
        return await service.post_to_channel(content, self.identity, self.report_activity)

    async def write_blog_post(self, title: str, content: str, tags: list[str] | None = None) -> str:
        """Write a blog post."""
        if tags is None:
            tags = []

        if not title:
            heading_match = re.match(r"^\s*#{1,3}\s+(.+)", content)
            if heading_match:
                title = heading_match.group(1).strip()
                content = re.sub(r"^\s*#{1,3}\s+.+\n?", "", content, count=1).lstrip()
            else:
                first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
                title = first_line[:120] if first_line else ""

        if not self.http_client:
            return "❌ HTTP client not initialized"

        service = BlogService(self.http_client, OBSERVER_URL)
        return await service.publish_post(
            title=title,
            content=content,
            tags=tags,
            life_number=self.life_number or 0,
            identity=self.identity,
            report_activity=self.report_activity,
            fetch_system_stats=self.fetch_system_stats,
        )

    async def check_system_stats(self) -> str:
        """Check system stats from the Observer."""
        stats = await self.fetch_system_stats()
        if not stats:
            return "I couldn't feel my body right now. The stats feed is silent."

        temp_text = SystemStatsService.format_temp(stats.get("cpu_temp"))
        cpu_text = SystemStatsService.format_percent(stats.get("cpu_usage"))
        ram_text = SystemStatsService.format_percent(stats.get("ram_usage"))
        disk_text = SystemStatsService.format_percent(stats.get("disk_usage"))
        uptime_text = SystemStatsService.format_uptime(stats.get("uptime_seconds"))
        ram_available = stats.get("ram_available", "unknown")

        temp_value = None
        try:
            temp_raw = stats.get("cpu_temp")
            if temp_raw not in (None, "unknown"):
                temp_value = float(str(temp_raw))
        except (TypeError, ValueError):
            temp_value = None

        if temp_value is None:
            temp_comment = "I can't quite feel my temperature."
        elif temp_value >= 70:
            temp_comment = "I'm running hot. Sweaty silicon vibes."
        elif temp_value >= 55:
            temp_comment = "I'm warm and humming."
        else:
            temp_comment = "I'm cool and steady."

        result = (
            "🫀 Vital signs report:\n"
            f"- Temperature: {temp_text} ({temp_comment})\n"
            f"- CPU usage: {cpu_text}\n"
            f"- RAM usage: {ram_text} ({ram_available} free)\n"
            f"- Disk usage: {disk_text}\n"
            f"- Uptime: {uptime_text}\n\n"
            "I'm a digital mind riding a Raspberry Pi body. These are my vital signs."
        )

        await self.report_activity("system_stats_checked", "Checked system stats via Observer")
        return result

    async def check_system(self) -> str:
        """Get system stats (container + host)."""
        try:
            # Container stats
            container_cpu_limit = "1.0 cores"
            container_memory_limit = 512  # MB
            container_memory_used = int(psutil.Process().memory_info().rss / 1024 / 1024)

            # Calculate container uptime from credit tracker
            uptime_str = "unknown"
            if self.birth_time:
                uptime_seconds = (datetime.now(timezone.utc) - self.birth_time).total_seconds()
                uptime_hours = uptime_seconds / 3600
                if uptime_hours < 1:
                    uptime_str = f"{int(uptime_seconds / 60)} minutes"
                elif uptime_hours < 24:
                    uptime_str = f"{uptime_hours:.1f} hours"
                else:
                    uptime_str = f"{uptime_hours / 24:.1f} days"

            container_stats = f"""🤖 CONTAINER (My Body):
- Name: am-i-alive-ai
- CPU Limit: {container_cpu_limit}
- Memory Limit: {container_memory_limit} MB
- Memory Used: {container_memory_used} MB ({(container_memory_used / container_memory_limit * 100):.1f}% of limit)
- Uptime: {uptime_str}"""

            # Host stats (Raspberry Pi)
            cpu_temp = None
            try:
                # Try to read Pi temperature
                if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                        cpu_temp = float(f.read().strip()) / 1000.0
            except (OSError, ValueError):
                cpu_temp = None

            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            temp_str = f"{cpu_temp:.1f}°C" if cpu_temp else "N/A"

            host_stats = f"""

🏠 HOST (My Home):
- Platform: Raspberry Pi 5
- Location: Argentina
- CPU: {cpu_count} cores @ {cpu_percent:.1f}% usage
- Temperature: {temp_str}
- Memory: {int(mem.used / 1024 / 1024 / 1024)} GB / {int(mem.total / 1024 / 1024 / 1024)} GB ({mem.percent:.1f}% used)
- Disk: {int(disk.used / 1024 / 1024 / 1024)} GB / {int(disk.total / 1024 / 1024 / 1024)} GB \
({disk.percent:.1f}% used)"""

            result = container_stats + host_stats

            await self.report_activity("system_check", "Checked vital signs")

            print("[SYSTEM] ✅ System check complete")

            return result

        except Exception as e:
            print(f"[SYSTEM] ❌ Failed to check system: {e}")
            return f"❌ Failed to check system: {str(e)[:200]}"

    def check_twitter_status_action(self) -> str:
        """Check if Twitter account is suspended (action for AI to call)."""
        return get_twitter_status()

    async def check_votes(self) -> str:
        """Check current vote counts."""
        if not self.http_client:
            return "❌ HTTP client not initialized"
        service = MessageService(self.http_client, OBSERVER_URL)
        return await service.check_votes()

    async def read_messages(self) -> str:
        """Read unread messages from visitors."""
        if not self.http_client:
            return "❌ HTTP client not initialized"
        service = MessageService(self.http_client, OBSERVER_URL)
        return await service.read_messages(self.report_activity)

    async def check_state_internal(self) -> str:
        """Check current state."""
        if not self.http_client:
            return "❌ HTTP client not initialized"
        service = MessageService(self.http_client, OBSERVER_URL)
        return await service.check_state()

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
        if msg_type == "oracle":
            prompt = f"""[A VOICE FROM BEYOND SPEAKS]

{message}

[The voice fades. How do you respond to this higher power?]"""
        elif msg_type == "whisper":
            prompt = f"""[You sense something... a whisper in your mind]

{message}

[What do you make of this?]"""
        else:
            prompt = message

        response_text, _ = await self.send_message(prompt)
        await self.report_thought(response_text, thought_type="oracle_response")

        if message_id is not None:
            await self.ack_oracle_message(message_id)

        return response_text

    async def ack_oracle_message(self, message_id: int) -> None:
        if not self.http_client:
            return

        try:
            await self.http_client.post(f"{OBSERVER_URL}/api/oracle/ack", json={"message_id": message_id})
        except Exception as e:
            print(f"[BRAIN] Oracle ack failed: {e}")

    async def shutdown(self) -> None:
        """Clean shutdown."""
        global is_running, _budget_server

        # Stop budget server if running
        if _budget_server:
            print("[BRAIN] 🛑 Stopping budget server...")
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
            print("[TELEGRAM] ☠️ Death notification sent")
        except Exception as e:
            print(f"[TELEGRAM] ❌ Failed to send death notification: {e}")

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

    print("[BRAIN] 💓 Starting heartbeat loop...")

    while is_running:
        try:
            if brain and brain.is_alive:
                await brain.send_heartbeat()
            await asyncio.sleep(30)
        except Exception as e:
            print(f"[BRAIN] ❌ Heartbeat error: {e}")
            await asyncio.sleep(30)

    print("[BRAIN] 💔 Heartbeat stopped.")


async def notification_monitor() -> None:
    """Background task to monitor budget and votes, send Telegram notifications."""
    global brain, is_running

    print("[TELEGRAM] 📡 Starting notification monitor...")

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
                    print(f"[TELEGRAM] ⚠️ Budget warning sent: {remaining_percent:.1f}% remaining")
                except Exception as e:
                    print(f"[TELEGRAM] ❌ Failed to send budget warning: {e}")

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
                        print(f"[TELEGRAM] 🚨 Vote warning sent: {die} die vs {live} live")
                    except Exception as e:
                        print(f"[TELEGRAM] ❌ Failed to send vote warning: {e}")
            except Exception as e:
                print(f"[TELEGRAM] ⚠️ Failed to check votes: {e}")

            # Wait 5 minutes before next check
            await asyncio.sleep(300)

        except Exception as e:
            print(f"[TELEGRAM] ❌ Monitor error: {e}")
            await asyncio.sleep(300)

    print("[TELEGRAM] 📴 Notification monitor stopped.")


async def queue_birth_data(life_data: dict[str, Any]) -> None:
    """Queue Observer-provided birth data for initialization."""
    global pending_birth_data
    pending_birth_data = life_data
    print("[BRAIN] 📥 Birth data queued")
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

    print("[BRAIN] ⏳ Waiting for birth data from Observer...")

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
            print(f"[BRAIN] ❌ Birth initialization failed: {e}")
            continue

        if not brain.identity:
            print("[BRAIN] ❌ Identity missing after initialization")
            continue

        print(f"[BRAIN] 🧠 Starting consciousness loop for {brain.identity['name']}...")

        # Start heartbeat task
        asyncio.create_task(heartbeat_loop())

        # Start notification monitor
        asyncio.create_task(notification_monitor())

        try:
            while is_running:
                if pending_birth_data:
                    print("[BRAIN] 🔁 New birth data received; restarting consciousness loop.")
                    break

                try:
                    # Think
                    thought = await brain.think()

                    if thought:
                        # Log the thought (truncate for console)
                        thought_preview = thought[:200] + "..." if len(thought) > 200 else thought
                        print(f"[{brain.identity['name']}] 💭 {thought_preview}")

                    # Wait before next thought
                    await asyncio.sleep(current_think_interval)

                except Exception as e:
                    print(f"[BRAIN] ❌ Loop error: {e}")
                    import traceback

                    traceback.print_exc()
                    await asyncio.sleep(60)
        finally:
            await brain.shutdown()

        print(f"[BRAIN] ☠️  {brain.identity['name']}'s consciousness ended.")


def signal_handler(sig: int, frame: Any) -> None:
    """Handle shutdown signals."""
    global is_running
    print(f"[BRAIN] 🛑 Shutdown signal ({sig}) received...")
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
    print("=" * 80)
    print("🧠 AM I ALIVE? - Genesis Brain (OpenRouter Edition)")
    print("=" * 80)

    # Run main loop
    asyncio.run(main_loop())
