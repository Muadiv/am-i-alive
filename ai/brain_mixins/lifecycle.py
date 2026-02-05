from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ..brain_shared import (
    BOOTSTRAP_MODE,
    OBSERVER_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    OPENROUTER_REFERER,
    OPENROUTER_TITLE,
)
from ..logging_config import logger
from ..moltbook_client import MoltbookClient
from ..services.action_handler import ActionHandler
from ..services.chat_service import ChatService
from ..services.echo_service import EchoService
from ..services.http_client_factory import HttpClientFactory
from ..services.lifecycle_service import LifecycleService
from ..services.model_retry_policy import ModelRetryPolicy
from ..services.observer_client import ObserverClient
from ..services.oracle_service import OracleService
from ..services.reporting_service import ReportingService
from ..services.prompt_service import PromptService
from ..services.system_stats_service import SystemStatsService


class BrainLifecycleMixin:
    def apply_birth_data(self, life_data: dict[str, Any]) -> None:
        self.life_number = life_data.get("life_number")
        self.is_alive = life_data.get("is_alive", True)
        self.birth_timestamp = life_data.get("birth_timestamp")
        self.identity = life_data.get("identity")
        self.bootstrap_mode = life_data.get("bootstrap_mode", BOOTSTRAP_MODE)
        self.budget_usd = life_data.get("budget_usd")
        self.life_info = life_data

    async def initialize(self, life_data: dict[str, Any]) -> None:
        headers = self.get_internal_headers()
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
        self.prompt_service = PromptService(self.http_client, OBSERVER_URL)
        self.system_stats_service = SystemStatsService(self.http_client, OBSERVER_URL)
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
        self.oracle_service = OracleService(
            self.send_message,
            self.report_thought,
            OBSERVER_URL,
            self.http_client,
        )
        self.action_handler = ActionHandler(
            self.http_client,
            OBSERVER_URL,
            self.observer_client,
            lambda: self.identity,
            lambda: self.life_number or 0,
            self.report_activity,
            self.fetch_system_stats,
        )

        self.thread_state.load(self.thread_state_path)
        if not self.thread_state.current_thread:
            name = self.identity.get("name", "Unknown") if self.identity else "Unknown"
            self.thread_state.current_thread = (
                f"Current thread: {name} just woke up. I'm learning the room, "
                "scanning my limits, and trying to stay alive."
            )
            self.thread_state.save(self.thread_state_path)

        if self.moltbook_api_key:
            self.moltbook_client = MoltbookClient(self.moltbook_api_key, self.http_client)
            logger.info("[MOLTBOOK] 🦞 Client initialized")
            self._load_moltbook_state()
        else:
            self.moltbook_client = None
            logger.warning("[MOLTBOOK] ⚠️  MOLTBOOK_API_KEY not set; Moltbook disabled")

        self.apply_birth_data(life_data)
        await self.load_memories()
        if not self.current_model:
            self.current_model = self.model_rotator.select_random_model(tier="ultra_cheap")
        await self.birth_sequence(life_data)

    async def birth_sequence(self, life_data: dict[str, Any]) -> None:
        identity = life_data.get("identity") or {}
        identity_name = identity.get("name", "Unknown")
        logger.info(f"[BRAIN] 👶 Beginning birth sequence for Life #{self.life_number}...")
        self.birth_time = datetime.now(timezone.utc)

        if not self.lifecycle_service:
            raise RuntimeError("Lifecycle service not initialized")

        credit_status = self.credit_tracker.get_status()
        current_model = self.current_model or {"name": "unknown", "input_cost": 0.0, "output_cost": 0.0}
        previous_death_cause = life_data.get("death_summary")
        previous_life = life_data.get("previous_life")

        bootstrap = await self.lifecycle_service.bootstrap_prompt(
            identity,
            credit_status,
            current_model,
            previous_death_cause,
            previous_life,
        )
        first_response, _ = await self.send_message(bootstrap)
        await self.report_thought(first_response, thought_type="awakening")

        await self.notify_birth()
        logger.info(f"[BRAIN] ✨ {identity_name} initialized")

    async def save_identity(self) -> None:
        await self.self_model_service.save_identity(self.identity or {})

    async def load_memories(self) -> None:
        self.memories = await self.lifecycle_service.load_memories(self.memories_path)

    async def fetch_system_stats(self) -> dict[str, Any]:
        if not self.observer_client:
            return {}
        return await self.observer_client.fetch_system_stats()

    async def handle_bankruptcy(self) -> None:
        logger.warning("[BRAIN] 💀 BANKRUPTCY! Out of credits!")
        await self.report_thought(
            "I'm out of resources... I can't think anymore... This might be the end...",
            thought_type="bankruptcy",
        )
        await self.report_activity("bankruptcy", "Ran out of API credits")

        try:
            await self.post_to_x("I'm running out of resources... Can anyone help? am-i-alive.muadiv.com.ar")
        except Exception as retry_error:
            logger.error(f"[BRAIN] ❌ Post failed during bankruptcy: {retry_error}")

        self.is_alive = False
        self.is_running = False

    async def notify_birth(self) -> None:
        if not self.observer_client:
            return
        if not self.identity:
            return
        payload = {
            "life_number": self.life_number,
            "ai_name": self.identity.get("name", "Unknown"),
            "icon": self.identity.get("icon", "🧠"),
            "model": self.current_model["name"] if self.current_model else "unknown",
            "bootstrap_mode": self.bootstrap_mode,
        }
        try:
            response = await self.observer_client.notify_birth(payload)
            logger.info(
                f"[BRAIN] 🎂 Birth notification sent: Life #{self.life_number}, Name: {payload['ai_name']}"
            )
            return response
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Birth notification failed: {e}")

    async def send_heartbeat(self) -> None:
        if not self.observer_client:
            return
        payload = {
            "tokens_used": self.tokens_used_life,
            "model": self.current_model.get("name") if self.current_model else "unknown",
        }
        await self.observer_client.send_heartbeat(payload)

    async def force_sync(self, sync_data: dict[str, Any]) -> None:
        if not self.lifecycle_service:
            return
        await self.lifecycle_service.force_sync(sync_data)

    async def ask_echo(self, question: str) -> str:
        if not self.echo_service:
            return "❌ Echo service not initialized"
        return await self.echo_service.ask_echo(question)

    async def shutdown(self) -> None:
        self.is_running = False
        if self.http_client:
            await self.http_client.aclose()
