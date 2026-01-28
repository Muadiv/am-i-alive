from __future__ import annotations

import asyncio
import random
from typing import Any, Callable

from ..model_config import MODELS, is_free_model_id
from ..model_rotator import ModelRotator


class ModelRetryPolicy:
    def __init__(
        self,
        model_rotator: ModelRotator,
        report_activity: Callable[[str, str], Any],
    ) -> None:
        self.model_rotator = model_rotator
        self.report_activity = report_activity
        self.rate_limit_retries = 0
        self.total_free_failures = 0

    async def handle_error(
        self,
        error_code: int,
        error_text: str,
        current_model: dict[str, Any] | None,
    ) -> tuple[bool, dict[str, Any] | None]:
        if error_code == 404:
            if current_model:
                await self.report_activity(
                    "model_error_auto_switch",
                    f"Model {current_model['name']} returned 404, switching automatically",
                )
            return await self._switch_on_free_failure(current_model)

        if error_code in {401, 403, 429, 500, 502, 503, 504}:
            return await self._switch_on_free_failure(current_model)

        lowered = error_text.lower()
        if "free" in lowered and "ended" in lowered:
            return await self._switch_on_free_failure(current_model)

        return False, current_model

    async def handle_rate_limit(
        self,
        current_model: dict[str, Any] | None,
    ) -> tuple[bool, dict[str, Any] | None]:
        self.rate_limit_retries += 1
        max_retries = 3

        if self.rate_limit_retries > max_retries:
            self.rate_limit_retries = 0
            return False, current_model

        backoff_seconds = 5 * (2 ** (self.rate_limit_retries - 1))
        await asyncio.sleep(backoff_seconds)

        old_model = current_model
        new_model = self.model_rotator.select_random_model(tier="free")

        if old_model and new_model and new_model["id"] == old_model["id"]:
            free_models = [m for m in MODELS["free"] if m["id"] != old_model["id"]]
            if free_models:
                new_model = random.choice(free_models)
                self.model_rotator.record_usage(new_model["id"])

        if old_model and new_model:
            await self.report_activity(
                "rate_limit_retry",
                f"Rate limited on {old_model['name']}, switched to {new_model['name']}",
            )

        return True, new_model

    async def _switch_on_free_failure(
        self,
        current_model: dict[str, Any] | None,
    ) -> tuple[bool, dict[str, Any] | None]:
        if not current_model:
            return True, self.model_rotator.select_random_model(tier="free")

        current_id = current_model.get("id", "")
        if is_free_model_id(current_id):
            failure_count = self.model_rotator.record_free_failure(current_id)
            self.total_free_failures += 1

            if failure_count < 3:
                new_model = self.model_rotator.select_random_model(tier="free")
                return True, new_model

            paid_model = self.model_rotator.get_next_paid_model(current_id)
            if paid_model:
                await self.report_activity(
                    "free_model_exhausted",
                    f"Switched to paid model {paid_model['name']} after repeated free failures",
                )
                return True, paid_model

        return True, self.model_rotator.select_random_model()
