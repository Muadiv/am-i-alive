from __future__ import annotations

from typing import Any, Callable

from .budget_service import BudgetService
from .system_stats_service import SystemStatsService


class HealthCheckService:
    def __init__(
        self,
        stats_service: SystemStatsService,
        budget_service: BudgetService,
        current_model: dict[str, Any] | None,
        send_message: Callable[..., Any],
    ) -> None:
        self.stats_service = stats_service
        self.budget_service = budget_service
        self.current_model = current_model
        self.send_message = send_message

    async def build_report(self) -> str:
        stats = await self.stats_service.fetch_stats()
        vital_signs = self.stats_service.build_vital_signs_report(stats)
        model_status = await self.budget_service.check_model_health(self.current_model, self.send_message)

        return "\n\n".join(
            [
                "🩺 HEALTH CHECK",
                vital_signs,
                model_status,
            ]
        )
