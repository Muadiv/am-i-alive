from __future__ import annotations

from typing import Any, Optional

import httpx

from .brain_mixins.actions import BrainActionMixin
from .brain_mixins.context import BrainContextMixin
from .brain_mixins.lifecycle import BrainLifecycleMixin
from .brain_mixins.moltbook import BrainMoltbookMixin
from .brain_mixins.openrouter import BrainOpenRouterMixin
from .brain_mixins.reporting import BrainReportingMixin
from .brain_mixins.thoughts import BrainThoughtMixin
from .brain_shared import (
    BOOTSTRAP_MODE,
    DONATION_BTC_ADDRESS,
    MOLTBOOK_AUTO_POST,
    MOLTBOOK_CHECK_INTERVAL_MINUTES,
    MOLTBOOK_MIN_POST_INTERVAL_MINUTES,
    MOLTBOOK_SUBMOLT,
    THINK_INTERVAL_SECONDS,
    MOLTBOOK_API_KEY,
    OBSERVER_URL,
    X_ACCESS_TOKEN,
    X_ACCESS_TOKEN_SECRET,
    X_API_KEY,
    X_API_SECRET,
    get_internal_headers,
)
from .actions import ActionExecutor
from .core.action_processor import ActionProcessor
from .core.brain_state import BrainState
from .credit_tracker import CreditTracker
from .logging_config import logger
from .model_rotator import ModelRotator
from .services.behavior_policy import BehaviorPolicy
from .moltbook_client import MoltbookClient
from .services.memory_selector import MemorySelector
from .services.budget_service import BudgetService
from .services.prompt_service import PromptService
from .services.sandbox_service import SandboxService
from .services.self_model_service import SelfModelService
from .services.system_stats_service import SystemStatsService
from .services.thread_state import ThreadState
from .services.twitter_service import TwitterService


class AIBrain(
    BrainContextMixin,
    BrainOpenRouterMixin,
    BrainThoughtMixin,
    BrainMoltbookMixin,
    BrainActionMixin,
    BrainReportingMixin,
    BrainLifecycleMixin,
):
    def __init__(self) -> None:
        self.chat_history: list[dict[str, str]] = []
        self.http_client: httpx.AsyncClient | None = None
        self.observer_url = OBSERVER_URL
        self.observer_client = None
        self.chat_service = None
        self.reporting_service = None
        self.model_retry_policy = None
        self.echo_service = None
        self.identity: dict[str, Any] | None = None
        self.credit_tracker: CreditTracker = CreditTracker(monthly_budget=5.00)
        self.model_rotator: ModelRotator = ModelRotator(self.credit_tracker.get_balance())
        self.current_model: dict[str, Any] | None = None
        self.action_executor = ActionExecutor(self)
        self.action_processor: ActionProcessor = ActionProcessor(self.action_executor, self.send_message, self.report_thought)
        self.budget_service = BudgetService(self.credit_tracker, self.model_rotator, self.report_activity)
        self.sandbox_service: SandboxService = SandboxService()
        self.prompt_service: PromptService | None = None
        self.self_model_service = SelfModelService("/app/workspace/identity.json")
        self.system_stats_service: SystemStatsService | None = None
        self.oracle_service = None
        self.lifecycle_service = None
        self.action_handler = None
        self.twitter_service = TwitterService(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
        self.life_number: int | None = None
        self.bootstrap_mode: str | None = BOOTSTRAP_MODE
        self.birth_timestamp: str | None = None
        self.birth_time = None
        self.life_info: dict[str, Any] | None = None
        self.tokens_used_life: int = 0
        self.is_alive: bool = True
        self.is_running: bool = True
        self.budget_usd: float | None = None
        self.memories: list[str] = []
        self.memories_path = "/app/memories"
        self.thread_state_path = "/app/workspace/thread_state.json"
        self.thread_state = ThreadState()
        self.current_topic = "survival strategy"
        self.behavior_policy = BehaviorPolicy(
            think_interval_seconds=THINK_INTERVAL_SECONDS,
            moltbook_min_post_interval_seconds=max(MOLTBOOK_MIN_POST_INTERVAL_MINUTES * 60, 1800),
        )
        self.memory_selector = MemorySelector()
        self.moltbook_client: MoltbookClient | None = None
        self.moltbook_api_key = MOLTBOOK_API_KEY
        self.moltbook_auto_post: bool = MOLTBOOK_AUTO_POST
        self.moltbook_submolt: str = MOLTBOOK_SUBMOLT
        self.moltbook_check_interval: int = MOLTBOOK_CHECK_INTERVAL_MINUTES * 60
        self.moltbook_last_check: float = 0.0
        self.moltbook_claimed: bool = False
        self.donation_btc_address: str | None = DONATION_BTC_ADDRESS
        self.moltbook_last_donation_ask: float = 0.0
        self.moltbook_state_path = "/app/workspace/moltbook_state.json"
        self.moltbook_comments_since_post: int = 0
        self.dns_failure_count: int = 0
        self.dns_pause_until: float = 0.0
        self.think_interval_min = THINK_INTERVAL_SECONDS
        self.think_interval_max = THINK_INTERVAL_SECONDS
        self.current_think_interval = THINK_INTERVAL_SECONDS

    @staticmethod
    def get_internal_headers() -> dict[str, str]:
        return get_internal_headers()

    @staticmethod
    def contains_sensitive_text(text: str) -> bool:
        from .brain_shared import contains_sensitive_text

        return contains_sensitive_text(text)

    @property
    def brain_state(self) -> BrainState:
        model_name = self.current_model.get("name", "unknown") if self.current_model else "unknown"
        return BrainState(
            identity=self.identity,
            model_name=model_name,
            balance=float(self.credit_tracker.get_balance()),
            life_number=self.life_number,
            bootstrap_mode=self.bootstrap_mode,
        )

    def _prepend_thread(self, content: str) -> str:
        if not self.thread_state.current_thread:
            return content
        if self.thread_state.current_thread in content:
            return content
        return f"{self.thread_state.current_thread}\n\n{content}"
