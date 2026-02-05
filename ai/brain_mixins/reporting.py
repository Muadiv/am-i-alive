from __future__ import annotations

from typing import Any

from ..logging_config import logger


class BrainReportingMixin:
    def _build_state(self):
        return self.brain_state

    async def report_thought(self, content: str, thought_type: str = "thought") -> None:
        if not self.http_client or not self.observer_client or not self.reporting_service:
            return

        try:
            cleaned_content = self.reporting_service.sanitize_thought(content)
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
