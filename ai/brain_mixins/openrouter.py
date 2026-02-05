from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Optional

import httpx

from ..logging_config import logger


class BrainOpenRouterMixin:
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

    def _should_pause_openrouter(self) -> bool:
        return time.monotonic() < self.dns_pause_until

    def _record_dns_failure(self) -> None:
        self.dns_failure_count += 1
        if self.dns_failure_count >= 3:
            self.dns_pause_until = time.monotonic() + 600

    def _reset_dns_failures(self) -> None:
        self.dns_failure_count = 0
        self.dns_pause_until = 0.0

    @staticmethod
    def _is_dns_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "name resolution" in message or "temporary failure" in message or "name or service not known" in message

    def _build_outage_response(self) -> tuple[str, dict[str, Any]]:
        response_text = "Network is unstable. I will keep thinking and try again soon."
        usage_stats: dict[str, Any] = {
            "model": self.current_model["name"] if self.current_model else "unknown",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "balance": self.credit_tracker.get_balance(),
            "status": "network_outage",
        }
        return response_text, usage_stats

    async def send_message(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        max_history_messages: int | None = None,
        max_chars: int | None = None,
        context_retry: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        if not self.current_model:
            self.current_model = self.model_rotator.select_random_model()
            logger.info(f"[BRAIN] 🧠 Selected model: {self.current_model['name']}")

        current_model = self.current_model

        max_chars = max_chars or self._estimate_max_chars()
        max_history_messages = max_history_messages or 40
        messages = self._build_messages(message, system_prompt, max_chars, max_history_messages)

        try:
            if not self.chat_service:
                raise RuntimeError("Chat service not initialized")

            if self._should_pause_openrouter():
                logger.warning("[BRAIN] ⚠️ DNS failures detected; skipping OpenRouter call for 10 minutes")
                return self._build_outage_response()

            retry_delays = [1, 3, 8]
            data = None
            for attempt, delay in enumerate(retry_delays, start=1):
                try:
                    data = await self.chat_service.send(current_model["id"], messages)
                    self._reset_dns_failures()
                    break
                except httpx.RequestError as exc:
                    if self._is_dns_error(exc):
                        self._record_dns_failure()
                        logger.warning(f"[BRAIN] ⚠️ DNS error (attempt {attempt}/{len(retry_delays)}): {exc}")
                        if self._should_pause_openrouter():
                            return self._build_outage_response()
                        if attempt < len(retry_delays):
                            await asyncio.sleep(delay + random.uniform(0.0, 0.5))
                            continue
                    raise

            if data is None:
                return self._build_outage_response()

            response_text, usage = self.chat_service.extract_response(data)
            input_tokens, output_tokens = self.chat_service.extract_usage(usage)
            self.tokens_used_life += input_tokens + output_tokens

            status_level = self.credit_tracker.charge(
                current_model["id"],
                input_tokens,
                output_tokens,
                float(current_model["input_cost"]),
                float(current_model["output_cost"]),
            )

            self.chat_history.append({"role": "user", "content": message})
            self.chat_history.append({"role": "assistant", "content": response_text})
            self._trim_chat_history(self._estimate_max_chars(), 40)

            self.model_rotator.credit_balance = self.credit_tracker.get_balance()
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
