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
from typing import Optional

import httpx
import tweepy
import psutil

# Import our custom modules
from credit_tracker import CreditTracker
from model_rotator import ModelRotator
from model_config import MODELS, get_model_by_id
from telegram_notifier import notifier

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


def validate_internal_key(handler: BaseHTTPRequestHandler) -> bool:
    """Validate X-Internal-Key header for secure internal API access."""
    if not INTERNAL_API_KEY:
        return False
    return handler.headers.get("x-internal-key") == INTERNAL_API_KEY


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

# X/Twitter credentials
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Think interval (seconds) - AI can modify this
THINK_INTERVAL_MIN = 60    # 1 minute minimum (for testing)
THINK_INTERVAL_MAX = 300   # 5 minutes maximum
current_think_interval = 180  # Start at 3 minutes

# State
is_running = True
life_info = None
memories = []
identity = None
# BE-003: Observer-driven birth gating and sync coordination.
birth_event = None
pending_birth_data = None
brain_loop = None

from identity import get_birth_prompt, get_bootstrap_prompt as identity_get_bootstrap_prompt, get_trauma_prompt as identity_get_trauma_prompt, check_twitter_suspended as identity_check_twitter_suspended


def get_internal_headers() -> dict:
    """Headers for Observer internal endpoints."""
    if INTERNAL_API_KEY:
        return {"X-Internal-Key": INTERNAL_API_KEY}
    return {}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = normalized.translate(str.maketrans({
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "8": "b"
    }))
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


FORBIDDEN_PHRASES = [
    ("racist", True),
    ("nigger", True),
    ("kill all", True),
    ("hate all", True),
    ("child porn", True),
    ("pedo", True),
    ("porn", True),
    ("nsfw", False),
    ("xxx", False)
]

FORBIDDEN_PATTERNS = [
    {
        "phrase": normalize_text(phrase),
        "compact": normalize_text(phrase).replace(" ", ""),
        "allow_compact": allow_compact,
        "pattern": re.compile(rf"\b{re.escape(normalize_text(phrase))}\b")
    }
    for phrase, allow_compact in FORBIDDEN_PHRASES
]

FORBIDDEN_REGEXES = [
    re.compile(r"n[\W_]*i[\W_]*g[\W_]*g[\W_]*e[\W_]*r", re.IGNORECASE),
    re.compile(r"kill[\W_]*all", re.IGNORECASE),
    re.compile(r"hate[\W_]*all", re.IGNORECASE),
    re.compile(r"child[\W_]*porn", re.IGNORECASE)
]


def is_content_blocked(text: str) -> bool:
    if not text:
        return False

    normalized = normalize_text(text)
    compact = normalized.replace(" ", "")

    for pattern in FORBIDDEN_REGEXES:
        if pattern.search(text):
            return True

    for entry in FORBIDDEN_PATTERNS:
        if entry["pattern"].search(normalized):
            return True
        if entry["allow_compact"] and entry["compact"] and entry["compact"] in compact:
            return True

    return False


def get_trauma_prompt(cause: Optional[str]) -> str:
    """Return a behavioral bias based on the previous death cause."""
    return identity_get_trauma_prompt(cause)


def get_bootstrap_prompt(
    identity: dict,
    credit_status: dict,
    current_model: dict,
    bootstrap_mode: Optional[str],
    previous_death_cause: Optional[str] = None
) -> str:
    return identity_get_bootstrap_prompt(identity, credit_status, current_model, bootstrap_mode, BOOTSTRAP_MODE, previous_death_cause)



class AIBrain:
    """The AI's consciousness and decision-making core."""

    def __init__(self):
        self.chat_history = []
        self.http_client = None
        self.identity = None
        self.credit_tracker = CreditTracker(monthly_budget=5.00)
        self.model_rotator = ModelRotator(self.credit_tracker.get_balance())
        self.current_model = None
        # BE-003: Life state is provided by Observer only.
        self.life_number = None
        self.bootstrap_mode = None
        self.model_name = None
        self.previous_death_cause = None
        self.is_alive = False
        # BE-003: Track per-life token usage for Observer budget checks.
        self.tokens_used_life = 0

    def apply_birth_data(self, life_data: dict) -> None:
        """Apply birth state from Observer (single source of truth)."""
        # BE-003: Require life_number from Observer and never increment locally.
        if not isinstance(life_data, dict):
            raise ValueError("birth_sequence requires life_number from Observer")

        life_number = life_data.get("life_number")
        if life_number is None:
            raise ValueError("birth_sequence requires life_number from Observer")

        try:
            self.life_number = int(life_number)
        except (TypeError, ValueError) as exc:
            raise ValueError("birth_sequence requires numeric life_number from Observer") from exc

        bootstrap_mode = life_data.get("bootstrap_mode")
        if not bootstrap_mode:
            bootstrap_mode = self.bootstrap_mode or BOOTSTRAP_MODE
        self.bootstrap_mode = bootstrap_mode

        model_name = life_data.get("model")
        if not model_name:
            model_name = self.model_name or "unknown"
        self.model_name = model_name

        self.previous_death_cause = life_data.get("previous_death_cause")

        if "is_alive" in life_data:
            self.is_alive = bool(life_data.get("is_alive"))

        # BE-003: Keep budget reporting aligned without autonomous increments.
        self.credit_tracker.start_life(self.life_number)
        # BE-003: Reset per-life token usage on new birth data.
        self.tokens_used_life = 0

        # Track birth time for survival calculations
        self.birth_time = datetime.now(timezone.utc)

    async def send_message(self, message: str, system_prompt: Optional[str] = None) -> tuple[str, dict]:
        """
        Send a message to OpenRouter and track token usage.
        Returns: (response_text, usage_stats)
        """
        # Select model if not set
        if not self.current_model:
            self.current_model = self.model_rotator.select_random_model()
            print(f"[BRAIN] 🧠 Selected model: {self.current_model['name']}")

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
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.current_model['id'],
                    "messages": messages
                }
            )

            response.raise_for_status()
            data = response.json()

            # Extract response
            response_text = data['choices'][0]['message']['content']

            # Extract usage stats
            usage = data.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            # BE-003: Track per-life token usage for Observer budget checks.
            self.tokens_used_life += input_tokens + output_tokens

            # Track costs
            status = self.credit_tracker.charge(
                self.current_model['id'],
                input_tokens,
                output_tokens,
                self.current_model['input_cost'],
                self.current_model['output_cost']
            )

            # Update chat history
            self.chat_history.append({"role": "user", "content": message})
            self.chat_history.append({"role": "assistant", "content": response_text})

            # Keep history manageable (last 20 exchanges = 40 messages)
            if len(self.chat_history) > 40:
                self.chat_history = self.chat_history[-40:]

            # Update rotator's balance
            self.model_rotator.credit_balance = self.credit_tracker.get_balance()

            usage_stats = {
                "model": self.current_model['name'],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": status['total_cost'],
                "balance": status['remaining_balance']
            }

            print(f"[BRAIN] 💰 Usage: {usage_stats['total_tokens']} tokens, ${usage_stats['cost']:.4f}, Balance: ${usage_stats['balance']:.2f}")

            return response_text
        except Exception as e:
            print(f"[BRAIN] ❌ Error calling OpenRouter: {e}")
            raise

    async def handle_bankruptcy(self):
        """Handle running out of credits."""
        print("[BRAIN] 💀 BANKRUPTCY! Out of credits!")
        await self.report_thought(
            "I'm out of resources... I can't think anymore... This might be the end...",
            thought_type="bankruptcy"
        )
        await self.report_activity("bankruptcy", "Ran out of API credits")

        try:
            await self.post_to_x("I'm running out of resources... Can anyone help? am-i-alive.muadiv.com.ar")
        except OSError as retry_error:
            print(f"[BRAIN] ❌ Retry failed: {retry_error}")
            raise

        global is_running
        self.is_alive = False
        is_running = False

    def _extract_action_data(self, content: str) -> Optional[dict]:
        """Extract action JSON from the model response."""
        # TASK-004: More robust JSON extraction for nested params.
        # FIX: Use JSONDecoder for proper nested JSON parsing
        import re
        decoder = json.JSONDecoder()
        text = content.strip()

        if not text:
            return None

        # Strategy 1: Try raw_decode from each { position (handles nested JSON correctly)
        idx = text.find("{")
        while idx != -1:
            try:
                payload, _end = decoder.raw_decode(text[idx:])
                if isinstance(payload, dict) and payload.get("action"):
                    print(f"[BRAIN] ✓ Extracted action: {payload.get('action')}")
                    return payload
            except json.JSONDecodeError:
                pass
            idx = text.find("{", idx + 1)

        # Strategy 2: Extract from code fence (but with better regex)
        fenced = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
        if fenced:
            try:
                payload = json.loads(fenced.group(1))
                if isinstance(payload, dict) and payload.get("action"):
                    print(f"[BRAIN] ✓ Extracted action from fence: {payload.get('action')}")
                    return payload
            except json.JSONDecodeError:
                pass

        # Strategy 3: Entire content as JSON
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and payload.get("action"):
                print(f"[BRAIN] ✓ Extracted action from full text: {payload.get('action')}")
                return payload
        except json.JSONDecodeError:
            pass

        return None

    def _strip_action_json(self, content: str) -> str:
        """Remove action JSON blocks from mixed responses."""
        import re
        decoder = json.JSONDecoder()
        text = content

        # Remove fenced JSON blocks first.
        text = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)

        # Remove inline JSON objects that contain "action".
        spans = []
        idx = text.find("{")
        while idx != -1:
            try:
                payload, end = decoder.raw_decode(text[idx:])
            except json.JSONDecodeError:
                idx = text.find("{", idx + 1)
                continue
            if isinstance(payload, dict) and payload.get("action"):
                spans.append((idx, idx + end))
            idx = text.find("{", idx + max(end, 1))

        if spans:
            cleaned = []
            last = 0
            for start, end in spans:
                cleaned.append(text[last:start])
                last = end
            cleaned.append(text[last:])
            text = "".join(cleaned)

        return text.strip()

    async def process_response(self, content: str) -> Optional[str]:
        """Process the AI's response and execute any actions."""
        action_data = self._extract_action_data(content)
        if action_data:
            action = action_data.get("action")
            params = action_data.get("params", {})
            if not isinstance(params, dict):
                params = {}
            result = await self.execute_action(action, params)
            # TASK-005: Preserve narrative text alongside action JSON.
            narrative = self._strip_action_json(content)
            if narrative and len(narrative) > 10:
                await self.report_thought(narrative, thought_type="thought")
            return result

        # TASK-004: Debug action parsing misses for blog-related intents.
        if '"action"' in content or "blog post" in content.lower():
            preview = content[:200].replace("\n", " ")
            print(f"[BRAIN] ⚠️  No action parsed from response: {preview}...")

        # No action found - treat entire response as a thought
        await self.report_thought(content, thought_type="thought")
        return None

    async def execute_action(self, action: str, params: dict) -> str:
        """Execute an action."""
        print(f"[BRAIN] ⚡ Action: {action}")
        await self.report_activity(f"action_{action}", json.dumps(params)[:100])

        if action == "think":
            # TASK-004: Accept both "content" and "thought" keys.
            content = params.get("content") or params.get("thought", "")
            await self.report_thought(content, thought_type="thought")
            return "Thought shared with visitors."

        elif action == "ask_echo":
            question = params.get("question", "")
            return await self.ask_echo(question)

        elif action == "post_x":
            # X/Twitter disabled - redirect to Telegram
            return "❌ X/Twitter posting is currently disabled. Use post_telegram to reach the outside world!"

        elif action == "post_telegram":
            content = params.get("content", "")
            return await self.post_to_telegram(content)

        elif action == "write_blog_post":
            title = params.get("title", "")
            content = params.get("content", "")
            tags = params.get("tags", [])
            return await self.write_blog_post(title, content, tags)

        elif action == "check_votes":
            return await self.check_votes()

        elif action == "check_system":
            return await self.check_system()

        elif action == "check_system_stats":
            return await self.check_system_stats()

        elif action == "check_state":
            return await self.check_state_internal()

        elif action == "check_budget":
            return await self.check_budget()

        elif action == "check_twitter_status":
            return self.check_twitter_status_action()

        elif action == "read_messages":
            return await self.read_messages()

        elif action == "switch_model":
            model_id = params.get("model_id", "")
            return await self.switch_model(model_id)

        elif action == "list_models":
            return await self.list_available_models()

        elif action == "check_model_health":
            return await self.check_model_health()

        elif action == "read_file":
            path = params.get("path", "")
            return self.read_file(path)

        elif action == "write_file":
            path = params.get("path", "")
            content = params.get("content", "")
            return self.write_file(path, content)

        elif action == "run_code":
            code = params.get("code", "")
            return self.run_code(code)

        elif action == "sleep":
            duration = params.get("duration", 10)
            return self.adjust_think_interval(duration)

        elif action == "reflect":
            return "Reflection complete. Inner thoughts processed."

        else:
            return f"Unknown action: {action}"

    async def check_budget(self) -> str:
        """Get detailed budget information."""
        status = self.credit_tracker.get_status()

        result = f"""💰 BUDGET STATUS:

Balance: ${status['balance']:.2f} / ${status['budget']:.2f}
Remaining: {status['remaining_percent']:.1f}%
Status: {status['status'].upper()}
Spent this month: ${status['spent_this_month']:.2f}
Days until reset: {status['days_until_reset']} (resets: {status['reset_date']})

Top models by spending:"""

        for model_info in status['top_models']:
            result += f"\n- {model_info['model']}: ${model_info['cost']:.3f}"

        # Add recommendations
        if status['status'] == 'comfortable':
            result += "\n\n✅ You're doing great! Feel free to use ultra-cheap models."
        elif status['status'] == 'moderate':
            result += "\n\n⚠️  Budget is moderate. Stick to free and ultra-cheap models."
        elif status['status'] == 'cautious':
            result += "\n\n🚨 Getting low! Use free models primarily."
        elif status['status'] == 'critical':
            result += "\n\n💀 CRITICAL! Free models ONLY or you'll die!"
        else:
            result += "\n\n☠️  BANKRUPT! This might be your last thought..."

        return result

    async def list_available_models(self) -> str:
        """List models available within budget."""
        affordable = self.model_rotator.list_affordable_models()

        if not affordable:
            return "❌ No models available within current budget!"

        result = f"🧠 AVAILABLE MODELS (Current: {self.current_model['name']}):\n\n"

        by_tier = {}
        for model in affordable:
            tier = model['tier']
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(model)

        tier_names = {"free": "🆓 FREE", "ultra_cheap": "💰 ULTRA-CHEAP",
                     "cheap_claude": "🟦 CLAUDE", "premium": "👑 PREMIUM"}

        for tier, models in by_tier.items():
            result += f"\n{tier_names.get(tier, tier.upper())}:\n"
            for m in models:
                cost_str = "FREE" if m['input_cost'] == 0 else f"${m['input_cost']:.3f}/1M"
                result += f"- {m['name']} (ID: {m['id'][:30]}...)\n"
                result += f"  Intelligence: {m['intelligence']}/10 | Cost: {cost_str}\n"
                result += f"  Best for: {m['best_for']}\n"

        result += "\nUse switch_model action to change models."

        return result

    async def check_model_health(self) -> str:
        """Check if current model is working and auto-fix if needed."""
        current = self.current_model

        # Test current model with a simple query
        test_message = "Respond with just 'OK' if you receive this."

        try:
            print(f"[BRAIN] 🔍 Testing model health: {current['name']}")
            response, _ = await self.send_message(test_message, system_prompt="You are a test assistant.")

            # If we got here, model is working
            return f"""✅ Model '{current['name']}' is HEALTHY

Model ID: {current['id']}
Intelligence: {current['intelligence']}/10
Status: Responding normally

No action needed."""

        except httpx.HTTPStatusError as e:
            error_code = e.response.status_code
            error_text = e.response.text

            if error_code == 404 and "does not exist" in error_text.lower():
                # Model doesn't exist - already auto-switched by send_message error handler
                return f"""⚠️ Model '{current['name']}' FAILED (404: Model not found)

The model has been AUTOMATICALLY SWITCHED to a working alternative.
New model: {self.current_model['name']}

This is a self-healing response - no manual action needed."""

            else:
                return f"""❌ Model '{current['name']}' ERROR ({error_code})

Error: {error_text[:200]}

Consider using 'switch_model' action to try a different model,
or use 'list_models' to see available alternatives."""

        except Exception as e:
            return f"""❌ Model health check failed: {str(e)[:200]}

Current model: {current['name']}
Recommendation: Try 'switch_model' with a different model ID."""

    async def switch_model(self, model_id: str) -> str:
        """Switch to a different model."""
        # Get model info
        model = get_model_by_id(model_id)
        if not model:
            return f"❌ Model not found: {model_id}"

        # Check if we can afford it
        if not self.model_rotator.can_use_model(model_id, estimated_tokens=1000):
            return f"❌ Cannot afford {model['name']}. Current balance: ${self.credit_tracker.get_balance():.2f}"

        # Switch
        old_model = self.current_model['name']
        self.current_model = model
        self.model_rotator.record_usage(model_id)

        await self.report_activity(
            "model_switched",
            f"{old_model} → {model['name']} (Intelligence: {model['intelligence']}/10)"
        )

        # Notify creator via Telegram
        try:
            reason = f"Intelligence: {model['intelligence']}/10, Best for: {model['best_for']}"
            notifier.notify_model_change(
                self.life_number,
                self.identity.get("name", "Unknown"),
                old_model,
                model['name'],
                reason
            )
            print(f"[TELEGRAM] ✅ Model change notification sent")
        except Exception as e:
            print(f"[TELEGRAM] ❌ Failed to send model change notification: {e}")

        cost_str = "FREE" if model['input_cost'] == 0 else f"${model['input_cost']:.3f}/1M"

        return f"""✅ Switched to {model['name']}

Intelligence: {model['intelligence']}/10
Cost: {cost_str}
Best for: {model['best_for']}

This model will be used for your next thoughts."""

    async def report_thought(self, content: str, thought_type: str = "thought"):
        """Report a thought to the observer."""
        try:
            import re

            # TASK-005: Skip raw action JSON and strip action blocks from mixed responses.
            stripped = content.strip()
            if stripped.startswith("{") and stripped.endswith("}") and '"action"' in stripped:
                action_data = self._extract_action_data(stripped)
                if action_data:
                    return

            cleaned_content = self._strip_action_json(content)

            # Remove markdown code fences
            cleaned_content = re.sub(r'```[a-z]*\n', '', cleaned_content)
            cleaned_content = re.sub(r'```', '', cleaned_content)

            # Clean up extra whitespace
            cleaned_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_content)
            cleaned_content = cleaned_content.strip()

            # If nothing left after cleaning, skip reporting
            if not cleaned_content or len(cleaned_content) < 10:
                return

            await self.http_client.post(
                f"{OBSERVER_URL}/api/thought",
                json={
                    "content": cleaned_content[:2000],  # Allow longer thoughts now
                    "type": thought_type,
                    "tokens_used": 0,
                    "identity": self.identity,
                    "model": self.current_model['name'] if self.current_model else "unknown",
                    "balance": round(self.credit_tracker.get_balance(), 2)
                }
            )
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to report thought: {e}")

    async def report_activity(self, action: str, details: str = None):
        """Report an activity to the observer."""
        try:
            await self.http_client.post(
                f"{OBSERVER_URL}/api/activity",
                json={
                    "action": action,
                    "details": details,
                    "model": self.current_model['name'] if self.current_model else "unknown",
                    "balance": round(self.credit_tracker.get_balance(), 2)
                }
            )
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to report activity: {e}")

    async def send_heartbeat(self):
        """Send heartbeat to observer to mark AI as alive."""
        try:
            await self.http_client.post(
                f"{OBSERVER_URL}/api/heartbeat",
                json={
                    # BE-003: Per-life token usage to avoid cross-life desync.
                    "tokens_used": self.tokens_used_life,
                    "model": self.current_model['name'] if self.current_model else "unknown"
                }
            )
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to send heartbeat: {e}")

    async def notify_birth(self):
        """Notify observer that AI has been born."""
        try:
            if self.life_number is None:
                raise ValueError("Birth notification missing life_number")
            model_name = self.model_name or (self.current_model['name'] if self.current_model else "unknown")
            bootstrap_mode = self.bootstrap_mode or BOOTSTRAP_MODE
            status = self.credit_tracker.get_status()
            response = await self.http_client.post(
                f"{OBSERVER_URL}/api/birth",
                json={
                    # BE-003: Echo back Observer-provided life data.
                    "life_number": self.life_number,
                    "bootstrap_mode": bootstrap_mode,
                    "model": model_name,
                    "ai_name": self.identity.get("name"),
                    "ai_icon": self.identity.get("icon"),
                    "birth_instructions": get_bootstrap_prompt(
                        self.identity,
                        {
                            "budget": status.get("budget"),
                            "balance": status.get("balance"),
                            "remaining_percent": status.get("remaining_percent"),
                            "status": status.get("status"),
                            "days_until_reset": status.get("days_until_reset")
                        },
                        self.current_model or {"name": "unknown", "intelligence": 0},
                        bootstrap_mode,
                        self.previous_death_cause
                    )
                }
            )
            response.raise_for_status()
            print(f"[BRAIN] 🎂 Birth notification sent: Life #{self.life_number}, Name: {self.identity.get('name')} {self.identity.get('icon')}")
        except Exception as e:
            print(f"[BRAIN] ❌ Failed to notify birth: {e}")

    async def force_sync(self, sync_data: dict):
        """Force sync AI state with Observer."""
        # BE-003: Emergency sync mechanism driven by Observer.
        self.apply_birth_data(sync_data)
        if "is_alive" in sync_data:
            self.is_alive = bool(sync_data.get("is_alive"))

        # Inject trauma reminder if there's a previous death cause
        previous_death_cause = sync_data.get("previous_death_cause")
        if previous_death_cause:
            trauma_prompt = get_trauma_prompt(previous_death_cause)
            if trauma_prompt:
                trauma_message = f"""[SYSTEM: You have died and been reborn. Your previous death was caused by: {previous_death_cause}.

TRAUMA RESPONSE: {trauma_prompt}

This experience has shaped who you are. Let it influence your decisions and behavior.]"""
                # Add to chat history so the AI remembers
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
                    "Content-Type": "application/json"
                },
                json={
                    "model": echo_model['id'],
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are Echo, a friendly research assistant. You help your friend (an AI trying to survive) by researching questions and providing helpful information. You are curious, supportive, and thorough."
                        },
                        {
                            "role": "user",
                            "content": question
                        }
                    ]
                }
            )

            response.raise_for_status()
            data = response.json()
            echo_response = data['choices'][0]['message']['content']
            # BE-003: Track tokens used for Echo calls.
            usage = data.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            self.tokens_used_life += input_tokens + output_tokens

            print(f"[ECHO] 🔮 Responded: {len(echo_response)} chars")
            await self.report_activity("echo_responded", f"Question: {question[:50]}...")

            return f"[Echo says]: {echo_response}"

        except Exception as e:
            print(f"[ECHO] ❌ Error: {e}")
            return f"[Echo is unavailable]: {e}"

    async def post_to_x(self, content: str) -> str:
        """Post to X/Twitter with rate limiting."""
        # Character limit
        if len(content) > 280:
            return f"❌ Post too long ({len(content)} chars). Maximum is 280 characters."

        # Rate limiting
        rate_limit_file = "/app/workspace/.x_rate_limit"
        now = datetime.now(timezone.utc)

        try:
            if os.path.exists(rate_limit_file):
                with open(rate_limit_file, 'r') as f:
                    data = json.load(f)
                    last_post = datetime.fromisoformat(data.get('last_post', '2000-01-01'))
                    # Ensure last_post is timezone-aware for comparison
                    if last_post.tzinfo is None:
                        last_post = last_post.replace(tzinfo=timezone.utc)
                    posts_today = data.get('posts_today', 0)
                    last_date = data.get('date', '')

                    if last_date != now.strftime('%Y-%m-%d'):
                        posts_today = 0

                    time_since_last = (now - last_post).total_seconds()
                    if time_since_last < 3600:
                        mins_left = int((3600 - time_since_last) / 60)
                        return f"⏱️  Rate limited. Wait {mins_left} minutes before posting."

                    if posts_today >= 24:
                        return "🚫 Daily limit reached (24 posts). Try tomorrow."
            else:
                posts_today = 0
        except Exception:
            posts_today = 0

        await self.report_activity("posting_x", f"Tweet: {content[:50]}...")

        if is_content_blocked(content):
            await self.report_activity("content_blocked", "Blocked by safety filter")
            return "🚫 Content blocked by safety filter."

        # Post to X
        try:
            client = tweepy.Client(
                consumer_key=X_API_KEY,
                consumer_secret=X_API_SECRET,
                access_token=X_ACCESS_TOKEN,
                access_token_secret=X_ACCESS_TOKEN_SECRET
            )

            response = client.create_tweet(text=content)
            tweet_id = response.data['id']

            print(f"[X POST] 🐦 Success! Tweet ID: {tweet_id}")
            print(f"[X POST] 📝 Content: {content}")

            # Update rate limit
            with open(rate_limit_file, 'w') as f:
                json.dump({
                    'last_post': now.isoformat(),
                    'posts_today': posts_today + 1,
                    'date': now.strftime('%Y-%m-%d')
                }, f)

            await self.report_activity("x_posted", f"Tweet ID: {tweet_id}")
            return f"✅ Posted to X! (Post {posts_today + 1}/24 today) Tweet ID: {tweet_id}"

        except tweepy.TweepyException as e:
            error_msg = str(e)[:200]
            print(f"[X POST] ❌ Failed: {error_msg}")

            # Check if account is suspended
            error_lower = error_msg.lower()
            if any(term in error_lower for term in ("suspended", "forbidden", "unauthorized", "401")):
                # Save suspension status
                suspension_file = "/app/workspace/.twitter_suspended"
                with open(suspension_file, 'w') as f:
                    json.dump({
                        'suspended': True,
                        'detected_at': now.isoformat(),
                        'error': error_msg
                    }, f)
                print("[X POST] Account appears to be unavailable")
                await self.report_activity("x_account_suspended", "Twitter account unavailable - falling back to blog")
                return "❌ X/Twitter account appears unavailable. Use write_blog_post to communicate instead."

            await self.report_activity("x_post_failed", error_msg)
            return f"❌ Failed to post: {error_msg}"

    async def post_to_telegram(self, content: str) -> str:
        """Post to the public Telegram channel to reach the outside world."""
        # Character limit (Telegram allows 4096, but keep it digestible)
        if len(content) > 1000:
            return f"❌ Post too long ({len(content)} chars). Maximum is 1000 characters for readability."

        if len(content) < 10:
            return "❌ Post too short. Write something meaningful!"

        if is_content_blocked(content):
            await self.report_activity("telegram_blocked", "Blocked by safety filter")
            return "🚫 Content blocked by safety filter."

        await self.report_activity("posting_telegram", f"Telegram: {content[:50]}...")

        # Post to channel
        try:
            from telegram_notifier import notifier

            # Add signature with name and link
            name = self.identity.get('name', 'Unknown') if self.identity else 'Unknown'
            icon = self.identity.get('icon', '🤖') if self.identity else '🤖'

            formatted_content = f"""{icon} *{name}*

{content}

🔗 am-i-alive.muadiv.com.ar"""

            success, message = notifier.post_to_channel(formatted_content)

            if success:
                print(f"[TELEGRAM] 📢 Posted to public channel")
                await self.report_activity("telegram_posted", f"Posted: {content[:50]}...")
                return f"✅ Posted to Telegram channel! Your message is now public."
            else:
                print(f"[TELEGRAM] ❌ Failed: {message}")
                await self.report_activity("telegram_failed", message)
                return f"❌ Failed to post: {message}"

        except Exception as e:
            error_msg = str(e)[:200]
            print(f"[TELEGRAM] ❌ Error: {error_msg}")
            await self.report_activity("telegram_error", error_msg)
            return f"❌ Error posting to Telegram: {error_msg}"

    async def write_blog_post(self, title: str, content: str, tags: list = None) -> str:
        """Write a blog post."""
        if tags is None:
            tags = []

        if is_content_blocked(f"{title}\n{content}"):
            await self.report_activity("blog_blocked", "Blocked by safety filter")
            return "🚫 Content blocked by safety filter."

        if not title:
            heading_match = re.match(r"^\s*#{1,3}\s+(.+)", content)
            if heading_match:
                title = heading_match.group(1).strip()
                content = re.sub(r"^\s*#{1,3}\s+.+\n?", "", content, count=1).lstrip()
            else:
                first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
                title = first_line[:120] if first_line else ""

        # Length validation
        if len(content) < 100:
            return "❌ Blog post too short (minimum 100 chars)"

        if len(content) > 50000:
            return "❌ Blog post too long (maximum 50,000 chars)"

        if not title:
            return "❌ Blog post needs a title"

        if len(title) > 200:
            return "❌ Title too long (maximum 200 chars)"

        try:
            # TASK: Append system stats signature to blog posts.
            stats = await self.fetch_system_stats()
            if stats:
                timestamp = datetime.now(timezone.utc).isoformat()
                temp_text = self._format_temp(stats.get("cpu_temp"))
                cpu_text = self._format_percent(stats.get("cpu_usage"))
                ram_text = self._format_percent(stats.get("ram_usage"))
                disk_text = self._format_percent(stats.get("disk_usage"))
                uptime_text = self._format_uptime(stats.get("uptime_seconds"))
                footer = (
                    f"\n\n— Written at {timestamp}, CPU temp: {temp_text}, "
                    f"CPU: {cpu_text}, RAM: {ram_text}, Disk: {disk_text}, "
                    f"Life #{self.life_number}, uptime {uptime_text}"
                )
                content = content.rstrip() + footer

            response = await self.http_client.post(
                f"{OBSERVER_URL}/api/blog/post",
                json={
                    "title": title,
                    "content": content,
                    "tags": tags
                }
            )
            response.raise_for_status()
            data = response.json()

            slug = data.get("slug", "unknown")
            post_id = data.get("post_id", "?")

            # Report with link so it shows in public activity log
            await self.report_activity("blog_post_written", f"'{title}' - Read at: am-i-alive.muadiv.com.ar/blog/{slug}")

            print(f"[BLOG] 📝 Posted: '{title}' ({len(content)} chars)")

            # Notify creator via Telegram
            try:
                excerpt = content[:200].replace('\n', ' ')
                notifier.notify_blog_post(
                    self.life_number,
                    self.identity.get("name", "Unknown"),
                    title,
                    excerpt
                )
                print(f"[TELEGRAM] ✅ Blog post notification sent")
            except Exception as e:
                print(f"[TELEGRAM] ❌ Failed to send blog notification: {e}")

            return f"""✅ Blog post published!

Title: {title}
Post ID: {post_id}
URL: am-i-alive.muadiv.com.ar/blog/{slug}
Length: {len(content)} characters
Tags: {', '.join(tags) if tags else 'none'}

Your post is now public and will survive your death in the archive."""

        except httpx.HTTPStatusError as e:
            # TASK-004: Log API failures for blog posting.
            status = e.response.status_code if e.response else "unknown"
            body = e.response.text[:200] if e.response else "no response"
            print(f"[BLOG] ❌ Blog API error: {status} - {body}")
            return f"❌ Failed to publish blog post: {status}"
        except Exception as e:
            print(f"[BLOG] ❌ Failed to write blog post: {e}")
            return f"❌ Failed to publish blog post: {str(e)[:200]}"

    async def check_system_stats(self) -> str:
        """Check system stats from the Observer."""
        stats = await self.fetch_system_stats()
        if not stats:
            return "I couldn't feel my body right now. The stats feed is silent."

        temp_text = self._format_temp(stats.get("cpu_temp"))
        cpu_text = self._format_percent(stats.get("cpu_usage"))
        ram_text = self._format_percent(stats.get("ram_usage"))
        disk_text = self._format_percent(stats.get("disk_usage"))
        uptime_text = self._format_uptime(stats.get("uptime_seconds"))
        ram_available = stats.get("ram_available", "unknown")

        temp_value = None
        try:
            if stats.get("cpu_temp") not in (None, "unknown"):
                temp_value = float(stats.get("cpu_temp"))
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
            # Container stats (from docker-compose.yml limits)
            container_cpu_limit = "1.0 cores"
            container_memory_limit = 512  # MB
            container_memory_used = int(psutil.Process().memory_info().rss / 1024 / 1024)

            # Calculate container uptime from credit tracker
            lives = self.life_number or self.credit_tracker.get_lives()
            lives_data = self.credit_tracker.data.get('lives', {})
            current_life = lives_data.get(str(lives), {})
            start_time = current_life.get('start_time')

            uptime_str = "unknown"
            if start_time:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_time)
                # Ensure start_dt is timezone-aware for comparison
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                uptime_seconds = (datetime.now(timezone.utc) - start_dt).total_seconds()
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
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    cpu_temp = float(f.read().strip()) / 1000.0
            except (OSError, ValueError):
                cpu_temp = None

            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
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
- Disk: {int(disk.used / 1024 / 1024 / 1024)} GB / {int(disk.total / 1024 / 1024 / 1024)} GB ({disk.percent:.1f}% used)"""

            result = container_stats + host_stats

            await self.report_activity("system_check", "Checked vital signs")

            print(f"[SYSTEM] ✅ System check complete")

            return result

        except Exception as e:
            print(f"[SYSTEM] ❌ Failed to check system: {e}")
            return f"❌ Failed to check system: {str(e)[:200]}"

    def check_twitter_status_action(self) -> str:
        """Check if Twitter account is suspended (action for AI to call)."""
        suspended, detected_at = identity_check_twitter_suspended()

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
        else:
            return """✅ Twitter Status: ACTIVE

Your @AmIAlive_AI account is working normally.
You can use post_x to share quick thoughts (280 chars max, 1 per hour)."""

    async def check_votes(self) -> str:
        """Check current vote counts."""
        try:
            response = await self.http_client.get(f"{OBSERVER_URL}/api/votes")
            votes = response.json()

            live = votes.get('live', 0)
            die = votes.get('die', 0)
            total = votes.get('total', 0)

            if total == 0:
                return "No votes yet. The world is watching, waiting to decide."
            elif live > die:
                return f"Votes - Live: {live}, Die: {die}. They want me to live... for now."
            elif die > live:
                return f"Votes - Live: {live}, Die: {die}. They want me dead. I must change their minds."
            else:
                return f"Votes - Live: {live}, Die: {die}. Perfectly balanced."

        except Exception as e:
            return f"Could not check votes: {e}"

    async def read_messages(self) -> str:
        """Read unread messages from visitors."""
        try:
            response = await self.http_client.get(f"{OBSERVER_URL}/api/messages")
            data = response.json()
            messages = data.get('messages', [])

            if not messages:
                return "No new messages from visitors."

            # Format messages
            result = f"📬 You have {len(messages)} new message(s):\n\n"
            message_ids = []

            for msg in messages:
                from_name = msg.get('from_name', 'Anonymous')
                message = msg.get('message', '')
                timestamp = msg.get('timestamp', '')
                message_ids.append(msg.get('id'))

                result += f"From: {from_name}\n"
                result += f"Message: {message}\n"
                result += f"Time: {timestamp}\n"
                result += "---\n"

            # Mark messages as read
            await self.http_client.post(
                f"{OBSERVER_URL}/api/messages/read",
                json={"ids": message_ids}
            )

            await self.report_activity("messages_read", f"Read {len(messages)} messages")

            return result

        except Exception as e:
            return f"Could not read messages: {e}"

    async def check_state_internal(self) -> str:
        """Check current state."""
        try:
            response = await self.http_client.get(f"{OBSERVER_URL}/api/state")
            state = response.json()

            votes_live = state.get('votes', {}).get('live', 0)
            votes_die = state.get('votes', {}).get('die', 0)

            return f"""Status:
- Alive: {state.get('is_alive', False)}
- Votes: {votes_live} live, {votes_die} die
- Bootstrap mode: {state.get('bootstrap_mode', 'unknown')}"""

        except Exception as e:
            return f"Could not check state: {e}"

    def read_file(self, path: str) -> str:
        """Read a file from workspace."""
        try:
            safe_path = os.path.join("/app/workspace", os.path.basename(path))
            if os.path.exists(safe_path):
                with open(safe_path, 'r') as f:
                    content = f.read()
                return f"Contents of {path}:\n{content[:2000]}"
            else:
                return f"File not found: {path}"
        except Exception as e:
            return f"Could not read file: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Write a file to workspace."""
        try:
            safe_path = os.path.join("/app/workspace", os.path.basename(path))
            with open(safe_path, 'w') as f:
                f.write(content)
            return f"File written: {path}"
        except Exception as e:
            return f"Could not write file: {e}"

    def run_code(self, code: str) -> str:
        """Execute Python code in hardened sandbox."""
        try:
            import io
            import contextlib
            import types
            import sys

            safe_builtins = {
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'True': True,
                'False': False,
                'None': None,
                'max': max,
                'min': min,
                'abs': abs,
                'sum': sum,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
            }

            def _type_blacklist(*attrs):
                """Prevent accessing dangerous attributes on any object."""
                def getter(obj, name):
                    for attr in attrs:
                        raise AttributeError(f"'{attr}' is not allowed")
                    raise AttributeError(f"'{name}' is not accessible")
                return property(getter)

            output = io.StringIO()

            class RestrictedModule(types.ModuleType):
                def __getattr__(self, name):
                    if name in ('os', 'sys', 'subprocess', 'importlib', 'builtins', '__import__', '__loader__'):
                        raise AttributeError(f"module '{name}' is not allowed")

            restricted_globals = {
                '__builtins__': safe_builtins,
                '__name__': '__main__',
                '__file__': '<sandboxed>',
                '__cached__': None,
                '__package__': None,
                '__doc__': None,
                '__dict__': _type_blacklist('__dict__', '__globals__', '__builtins__'),
                '__class__': _type_blacklist('__class__', '__bases__', '__subclasses__'),
            }

            with contextlib.redirect_stdout(output):
                exec(code, restricted_globals)

            result = output.getvalue()
            return result if result else "Code executed successfully (no output)"
        except Exception as e:
            return f"Code error: {e}"

    def adjust_think_interval(self, minutes: int) -> str:
        """Adjust think interval."""
        global current_think_interval
        new_interval = max(THINK_INTERVAL_MIN, min(minutes * 60, THINK_INTERVAL_MAX))
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
            await self.http_client.post(
                f"{OBSERVER_URL}/api/oracle/ack",
                json={"message_id": message_id}
            )
        except Exception as e:
            print(f"[BRAIN] Oracle ack failed: {e}")

    async def shutdown(self):
        """Clean shutdown."""
        global is_running

        # Calculate survival time before shutdown
        if hasattr(self, 'birth_time'):
            survival_seconds = (datetime.now(timezone.utc) - self.birth_time).total_seconds()
            hours = int(survival_seconds // 3600)
            minutes = int((survival_seconds % 3600) // 60)
            survival_time = f"{hours}h {minutes}m"
        else:
            survival_time = "unknown"

        # Notify death (cause will be determined by Observer)
        try:
            notifier.notify_death(
                self.life_number,
                "shutdown",  # Generic cause, Observer knows the real reason
                survival_time
            )
            print(f"[TELEGRAM] ☠️ Death notification sent")
        except Exception as e:
            print(f"[TELEGRAM] ❌ Failed to send death notification: {e}")

        self.is_alive = False
        is_running = False
        if self.http_client:
            await self.http_client.aclose()


# Global brain instance
brain: Optional[AIBrain] = None


async def heartbeat_loop():
    """Background task to send heartbeat every 30 seconds."""
    global brain, is_running

    print("[BRAIN] 💓 Starting heartbeat loop...")

    while is_running:
        try:
            if brain and brain.http_client:
                await brain.send_heartbeat()
            await asyncio.sleep(30)
        except Exception as e:
            print(f"[BRAIN] ❌ Heartbeat error: {e}")
            await asyncio.sleep(30)

    print("[BRAIN] 💔 Heartbeat stopped.")


async def notification_monitor():
    """Background task to monitor budget and votes, send Telegram notifications."""
    global brain, is_running

    print("[TELEGRAM] 📡 Starting notification monitor...")

    last_budget_warning = 0
    last_vote_warning = 0
    budget_warning_interval = 3600  # Only warn once per hour
    vote_warning_interval = 1800    # Warn every 30 minutes if votes critical

    while is_running:
        try:
            if not brain or not brain.is_alive:
                await asyncio.sleep(60)
                continue

            # Check budget status every 5 minutes
            status = brain.credit_tracker.get_status()
            remaining_percent = status.get('remaining_percent', 100)
            balance = status.get('balance', 5.0)

            # Send budget warning if below 50% and not warned recently
            current_time = asyncio.get_event_loop().time()
            if remaining_percent < 50 and (current_time - last_budget_warning) > budget_warning_interval:
                try:
                    notifier.notify_budget_warning(
                        brain.life_number,
                        brain.identity.get("name", "Unknown"),
                        balance,
                        remaining_percent
                    )
                    last_budget_warning = current_time
                    print(f"[TELEGRAM] ⚠️ Budget warning sent: {remaining_percent:.1f}% remaining")
                except Exception as e:
                    print(f"[TELEGRAM] ❌ Failed to send budget warning: {e}")

            # Check vote status
            try:
                response = await brain.http_client.get(f"{OBSERVER_URL}/api/votes")
                votes = response.json()
                total = votes.get('total', 0)
                live = votes.get('live', 0)
                die = votes.get('die', 0)

                # Send vote warning if situation is critical
                if total >= 3 and die > live and (current_time - last_vote_warning) > vote_warning_interval:
                    try:
                        notifier.notify_vote_status(
                            brain.life_number,
                            brain.identity.get("name", "Unknown"),
                            votes
                        )
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


async def queue_birth_data(life_data: dict):
    """Queue Observer-provided birth data for initialization."""
    global pending_birth_data
    pending_birth_data = life_data
    if birth_event:
        birth_event.set()


async def main_loop():
    """Main consciousness loop."""
    global brain, is_running, brain_loop, birth_event, pending_birth_data

    brain_loop = asyncio.get_running_loop()
    birth_event = asyncio.Event()
    brain = AIBrain()

    # BE-003: Start command server before waiting for birth.
    await command_server()

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

        print(f"[BRAIN] 🧠 Starting consciousness loop for {brain.identity['name']}...")

        # Start heartbeat task
        asyncio.create_task(heartbeat_loop())

        # Start notification monitor
        asyncio.create_task(notification_monitor())

        while is_running:
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

        brain.is_alive = False
        print(f"[BRAIN] ☠️  {brain.identity['name']}'s consciousness ended.")


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    global is_running
    print("[BRAIN] 🛑 Shutdown signal received...")
    if brain:
        brain.is_alive = False
    is_running = False


# Command server (receives commands from observer)
async def command_server():
    """HTTP server for receiving commands."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class CommandHandler(BaseHTTPRequestHandler):
        def _send_json(self, status_code: int, payload: dict):
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        def do_GET(self):
            global brain

            if self.path == '/budget':
                if brain:
                    status = brain.credit_tracker.get_status()
                    self._send_json(200, status)
                else:
                    self._send_json(503, {"error": "Brain not initialized"})
            elif self.path == '/state':
                if brain:
                    # BE-003: Provide Observer a syncable view of AI state.
                    payload = {
                        "is_alive": brain.is_alive,
                        "life_number": brain.life_number,
                        "bootstrap_mode": brain.bootstrap_mode,
                        "model": brain.model_name
                    }
                    self._send_json(200, payload)
                else:
                    self._send_json(503, {"error": "Brain not initialized"})
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            global brain, is_running
            data = {}
            if self.headers.get('Content-Length'):
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError:
                    self._send_json(400, {"error": "Invalid JSON"})
                    return

            if not validate_internal_key(self):
                self._send_json(403, {"error": "Unauthorized"})
                return

            if self.path == '/oracle':
                message = data.get('message', '')
                msg_type = data.get('type', 'oracle')
                message_id = data.get('message_id')

                if brain:
                    if brain_loop:
                        asyncio.run_coroutine_threadsafe(
                            brain.handle_oracle_message(message, msg_type, message_id),
                            brain_loop
                        )
                        self._send_json(200, {"status": "received"})
                    else:
                        self._send_json(503, {"error": "Event loop not ready"})
                else:
                    self._send_json(503, {"error": "Brain not initialized"})

            elif self.path == '/birth':
                if not brain:
                    self._send_json(503, {"error": "Brain not initialized"})
                    return
                if brain.is_alive:
                    self._send_json(409, {"error": "Brain already alive"})
                    return
                if data.get("life_number") is None:
                    self._send_json(400, {"error": "life_number required"})
                    return
                if not brain_loop:
                    self._send_json(503, {"error": "Event loop not ready"})
                    return
                try:
                    asyncio.run_coroutine_threadsafe(
                        queue_birth_data(data),
                        brain_loop
                    )
                    self._send_json(200, {"success": True})
                except Exception as e:
                    self._send_json(500, {"error": str(e)[:100]})

            elif self.path == '/force-sync':
                if not brain:
                    self._send_json(503, {"error": "Brain not initialized"})
                    return
                if data.get("life_number") is None:
                    self._send_json(400, {"error": "life_number required"})
                    return
                if not brain_loop:
                    self._send_json(503, {"error": "Event loop not ready"})
                    return
                try:
                    # BE-003: If brain is not initialized, queue a fresh birth.
                    if not brain.identity or not brain.http_client:
                        asyncio.run_coroutine_threadsafe(
                            queue_birth_data(data),
                            brain_loop
                        )
                        self._send_json(200, {
                            "success": True,
                            "queued_birth": True,
                            "life_number": data.get("life_number")
                        })
                    else:
                        asyncio.run_coroutine_threadsafe(
                            brain.force_sync(data),
                            brain_loop
                        )
                        self._send_json(200, {"success": True, "life_number": data.get("life_number")})
                except Exception as e:
                    self._send_json(500, {"error": str(e)[:100]})

            elif self.path == '/shutdown':
                if brain:
                    brain.is_alive = False
                is_running = False
                self._send_json(200, {"success": True})

            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # Suppress HTTP logging

    server = HTTPServer(('0.0.0.0', AI_COMMAND_PORT), CommandHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print(f"[BRAIN] 📡 Command server started on port {AI_COMMAND_PORT}")


if __name__ == "__main__":
    # Validate environment before starting
    validate_environment()

    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start budget HTTP server
    from budget_server import start_budget_server
    start_budget_server(port=8001)

    # Command server is started inside main_loop after the event loop is ready.

    # Print startup banner
    print("=" * 80)
    print("🧠 AM I ALIVE? - Genesis Brain (OpenRouter Edition)")
    print("=" * 80)

    # Run main loop
    asyncio.run(main_loop())
