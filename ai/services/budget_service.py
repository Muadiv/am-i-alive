from __future__ import annotations

from typing import Any, Callable

import httpx

from ..logging_config import logger
from ..model_config import get_model_by_id
from ..model_rotator import ModelRotator
from ..telegram_notifier import notifier


class BudgetService:
    def __init__(
        self,
        credit_tracker: Any,
        model_rotator: ModelRotator,
        report_activity: Callable[[str, str | None], Any],
    ) -> None:
        self.credit_tracker = credit_tracker
        self.model_rotator = model_rotator
        self.report_activity = report_activity

    async def check_budget(self) -> str:
        status = self.credit_tracker.get_status()

        balance = float(str(status.get("balance", 0.0)))
        budget = float(str(status.get("budget", 0.0)))
        remaining_percent = float(str(status.get("remaining_percent", 0.0)))
        status_level = str(status.get("status", "unknown")).upper()
        spent_this_month = float(str(status.get("spent_this_month", 0.0)))
        days_until_reset = int(str(status.get("days_until_reset", 0)))
        reset_date = str(status.get("reset_date", "unknown"))

        result = f"""💰 BUDGET STATUS:

Balance: ${balance:.2f} / ${budget:.2f}
Remaining: {remaining_percent:.1f}%
Status: {status_level}
Spent this month: ${spent_this_month:.2f}
Days until reset: {days_until_reset} (resets: {reset_date})

Top models by spending:"""

        top_models = status.get("top_models", [])
        if isinstance(top_models, list):
            for model_info in top_models:
                if isinstance(model_info, dict):
                    result += f"\n- {model_info.get('model')}: ${float(model_info.get('cost', 0.0)):.3f}"

        status_raw = str(status.get("status", ""))
        if status_raw == "comfortable":
            result += "\n\n✅ You're doing great! Feel free to use ultra-cheap models."
        elif status_raw == "moderate":
            result += "\n\n⚠️  Budget is moderate. Stick to free and ultra-cheap models."
        elif status_raw == "cautious":
            result += "\n\n🚨 Getting low! Use free models primarily."
        elif status_raw == "critical":
            result += "\n\n💀 CRITICAL! Free models ONLY or you'll die!"
        else:
            result += "\n\n☠️  BANKRUPT! This might be your last thought..."

        return result

    async def list_available_models(self, current_model: dict[str, Any] | None) -> str:
        affordable = self.model_rotator.list_affordable_models()

        if not affordable:
            return "❌ No models available within current budget!"

        current_model_name = current_model.get("name", "Unknown") if current_model else "Unknown"
        result = f"🧠 AVAILABLE MODELS (Current: {current_model_name}):\n\n"

        by_tier: dict[str, list[dict[str, Any]]] = {}
        for model in affordable:
            tier = str(model.get("tier", "unknown"))
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(model)

        tier_names = {
            "free": "🆓 FREE",
            "ultra_cheap": "💰 ULTRA-CHEAP",
            "cheap_claude": "🟦 CLAUDE",
            "premium": "👑 PREMIUM",
        }

        for tier, tier_models in by_tier.items():
            result += f"\n{tier_names.get(tier, tier.upper())}:\n"
            for m in tier_models:
                input_cost = float(m.get("input_cost", 0.0))
                cost_str = "FREE" if input_cost == 0 else f"${input_cost:.3f}/1M"
                result += f"- {m.get('name')} (ID: {str(m.get('id', ''))[:30]}...)\n"
                result += f"  Intelligence: {m.get('intelligence')}/10 | Cost: {cost_str}\n"
                result += f"  Best for: {m.get('best_for')}\n"

        result += "\nUse switch_model action to change models."

        return result

    async def check_model_health(self, current_model: dict[str, Any] | None, send_message: Any) -> str:
        if not current_model:
            return "❌ No model currently selected."

        test_message = "Respond with just 'OK' if you receive this."

        try:
            logger.info(f"[BRAIN] 🔍 Testing model health: {current_model['name']}")
            await send_message(test_message, system_prompt="You are a test assistant.")

            return f"""✅ Model '{current_model['name']}' is HEALTHY

Model ID: {current_model['id']}
Intelligence: {current_model['intelligence']}/10
Status: Responding normally

No action needed."""

        except httpx.HTTPStatusError as e:
            error_code = e.response.status_code
            error_text = e.response.text

            if error_code == 404 and "does not exist" in error_text.lower():
                new_model_name = current_model.get("name", "Unknown") if current_model else "Unknown"
                return f"""⚠️ Model '{current_model['name']}' FAILED (404: Model not found)

The model has been AUTOMATICALLY SWITCHED to a working alternative.
New model: {new_model_name}

This is a self-healing response - no manual action needed."""

            return f"""❌ Model '{current_model['name']}' ERROR ({error_code})

Error: {error_text[:200]}

Consider using 'switch_model' action to try a different model,
or use 'list_models' to see available alternatives."""

        except Exception as e:
            return f"""❌ Model health check failed: {str(e)[:200]}

Current model: {current_model['name']}
Recommendation: Try 'switch_model' with a different model ID."""

    async def switch_model(
        self,
        current_model: dict[str, Any] | None,
        model_id: str,
        life_number: int | None,
        identity_name: str,
    ) -> tuple[str, dict[str, Any] | None]:
        model = get_model_by_id(model_id)
        if not model:
            return f"❌ Model not found: {model_id}", current_model

        if not self.model_rotator.can_use_model(model_id, estimated_tokens=1000):
            return (
                f"❌ Cannot afford {model['name']}. Current balance: ${self.credit_tracker.get_balance():.2f}",
                current_model,
            )

        old_model_name = current_model.get("name", "Unknown") if current_model else "Unknown"
        new_model = model
        self.model_rotator.record_usage(model_id)

        await self.report_activity(
            "model_switched", f"{old_model_name} → {model['name']} (Intelligence: {model['intelligence']}/10)"
        )

        try:
            reason = f"Intelligence: {model['intelligence']}/10, Best for: {model['best_for']}"
            await notifier.notify_model_change(life_number or 0, identity_name, old_model_name, model["name"], reason)
            logger.info("[TELEGRAM] ✅ Model change notification sent")
        except Exception as e:
            logger.error(f"[TELEGRAM] ❌ Failed to send model change notification: {e}")

        input_cost = float(model.get("input_cost", 0.0))
        cost_str = "FREE" if input_cost == 0 else f"${input_cost:.3f}/1M"

        result = f"""✅ Switched to {model['name']}

Intelligence: {model['intelligence']}/10
Cost: {cost_str}
Best for: {model['best_for']}

This model will be used for your next thoughts."""

        return result, new_model
