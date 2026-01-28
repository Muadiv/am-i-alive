import json
import os
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TypedDict, cast

from .budget_aggregator import UsageEntry, aggregate_usage  # type: ignore
from .logging_config import logger

ModelCostEntry = dict[str, float]
UsageHistorySequence = Sequence[UsageEntry]

CREDITS_FILE = "/app/credits/balance.json"


class UsageHistoryEntry(TypedDict):
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class LifeModelUsage(TypedDict):
    input_tokens: int
    output_tokens: int
    cost: float


class LifeUsage(TypedDict):
    life_number: int
    input_tokens: int
    output_tokens: int
    total_cost: float
    models: dict[str, LifeModelUsage]


class AllTimeUsage(TypedDict):
    input_tokens: int
    output_tokens: int
    total_cost: float


class CreditData(TypedDict):
    monthly_budget_usd: float
    current_balance_usd: float
    reset_date: str
    total_lives: int
    current_life_number: int
    current_life_usage: LifeUsage
    all_time_usage: AllTimeUsage
    usage_monthly: float
    usage_by_model: dict[str, float]
    usage_history: list[UsageHistoryEntry]


class TopModelEntry(TypedDict):
    model: str
    cost: float


class CreditTracker:

    def __init__(self, monthly_budget: float = 5.00):
        self.monthly_budget: float = monthly_budget
        self.data: CreditData = self.load()

    def load(self) -> CreditData:
        if os.path.exists(CREDITS_FILE):
            try:
                with open(CREDITS_FILE, "r") as f:
                    raw = json.load(f)
                if not isinstance(raw, dict):
                    return self.create_new_data()
                data = cast(CreditData, raw)
                if not isinstance(data.get("usage_history"), list):
                    data["usage_history"] = []

                # Check if we need to reset monthly budget
                reset_date = datetime.fromisoformat(data.get("reset_date", "2000-01-01"))
                # Ensure reset_date is timezone-aware for comparison
                if reset_date.tzinfo is None:
                    reset_date = reset_date.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) >= reset_date:
                    # Monthly reset!
                    logger.info(f"[CREDITS] 🎉 Monthly budget reset! New balance: ${self.monthly_budget:.2f}")
                    data["current_balance_usd"] = self.monthly_budget
                    data["reset_date"] = self.get_next_reset_date()
                    data["usage_monthly"] = 0
                    self.save_if_changed(data)

                needs_save = False
                if "current_life_number" not in data:
                    needs_save = True
                current_life: object = data.get("current_life_usage")
                if not isinstance(current_life, dict):
                    needs_save = True
                else:
                    for key in ("life_number", "input_tokens", "output_tokens", "total_cost", "models"):
                        if key not in current_life:
                            needs_save = True
                            break

                all_time: object = data.get("all_time_usage")
                if not isinstance(all_time, dict):
                    needs_save = True
                else:
                    for key in ("input_tokens", "output_tokens", "total_cost"):
                        if key not in all_time:
                            needs_save = True
                            break

                data = self.ensure_usage_fields(data)
                if needs_save:
                    self.save_if_changed(data)
                return data
            except Exception as e:
                logger.error(f"[CREDITS] Error loading credits file: {e}")
                return self.create_new_data()
        else:
            return self.create_new_data()

    def create_new_data(self) -> CreditData:
        data: CreditData = {
            "monthly_budget_usd": self.monthly_budget,
            "current_balance_usd": self.monthly_budget,
            "reset_date": self.get_next_reset_date(),
            "total_lives": 0,
            "current_life_number": 0,
            "current_life_usage": self._new_life_usage(0),
            "all_time_usage": self._new_all_time_usage(),
            "usage_monthly": 0,
            "usage_by_model": {},
            "usage_history": [],
        }
        self.save_data(data)
        return data

    def _new_life_usage(self, life_number: int) -> LifeUsage:
        return {"life_number": int(life_number), "input_tokens": 0, "output_tokens": 0, "total_cost": 0.0, "models": {}}

    def _new_all_time_usage(self) -> AllTimeUsage:
        return {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}

    def ensure_usage_fields(self, data: CreditData) -> CreditData:
        if "current_life_number" not in data:
            data["current_life_number"] = data.get("total_lives", 0)

        life_number = data.get("current_life_number", 0) or 0
        try:
            life_number_int = int(life_number)
        except (TypeError, ValueError):
            life_number_int = 0

        current_life = data.get("current_life_usage")
        if not isinstance(current_life, dict):
            current_life = self._new_life_usage(life_number_int)
            data["current_life_usage"] = current_life

        current_life.setdefault("life_number", life_number_int)
        current_life.setdefault("input_tokens", 0)
        current_life.setdefault("output_tokens", 0)
        current_life.setdefault("total_cost", 0.0)
        current_life.setdefault("models", {})

        all_time = data.get("all_time_usage")
        if not isinstance(all_time, dict):
            all_time = self._new_all_time_usage()
            data["all_time_usage"] = all_time

        all_time.setdefault("input_tokens", 0)
        all_time.setdefault("output_tokens", 0)
        all_time.setdefault("total_cost", 0.0)

        return data

    def start_life(self, life_number: int) -> None:
        try:
            life_number = int(life_number)
        except (TypeError, ValueError):
            life_number = 0

        self.data = self.ensure_usage_fields(self.data)
        self.data["current_life_number"] = life_number
        self.data["current_life_usage"] = self._new_life_usage(life_number)
        if life_number > int(self.data.get("total_lives", 0) or 0):
            self.data["total_lives"] = life_number
        self.save()

    def get_next_reset_date(self) -> str:
        now = datetime.now(timezone.utc)
        # Reset on the 1st of next month (timezone-aware)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        return next_month.isoformat()

    def charge(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        input_cost_per_1m: float,
        output_cost_per_1m: float,
    ) -> str:
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
        total_cost = input_cost + output_cost

        self.data = self.ensure_usage_fields(self.data)
        current_life = self.data["current_life_usage"]
        current_life_number = self.data.get("current_life_number", 0)
        try:
            current_life_number_int = int(current_life_number)
        except (TypeError, ValueError):
            current_life_number_int = 0
        if not isinstance(current_life, dict):
            current_life = self._new_life_usage(current_life_number_int)
            self.data["current_life_usage"] = current_life
        if current_life.get("life_number") != current_life_number_int:
            current_life = self._new_life_usage(current_life_number_int)
            self.data["current_life_usage"] = current_life

        current_life = cast(LifeUsage, current_life)

        # Check if balance will go negative before deducting
        current_balance = float(self.data.get("current_balance_usd", 0.0) or 0.0)
        if current_balance - total_cost <= 0.01:
            return "BANKRUPT"
        self.data["current_balance_usd"] = current_balance - total_cost
        self.data["usage_monthly"] = float(self.data.get("usage_monthly", 0.0) or 0.0) + total_cost

        # Track by model
        usage_by_model = self.data.get("usage_by_model")
        if not isinstance(usage_by_model, dict):
            usage_by_model = {}
            self.data["usage_by_model"] = usage_by_model
        if model_id not in usage_by_model:
            usage_by_model[model_id] = 0.0
        usage_by_model[model_id] = float(usage_by_model.get(model_id, 0.0) or 0.0) + total_cost

        current_life["input_tokens"] = int(current_life["input_tokens"]) + input_tokens
        current_life["output_tokens"] = int(current_life["output_tokens"]) + output_tokens
        current_life["total_cost"] = float(current_life["total_cost"]) + total_cost
        life_models = current_life.get("models")
        if not isinstance(life_models, dict):
            life_models = {}
            current_life["models"] = life_models
        if model_id not in life_models:
            life_models[model_id] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        model_usage = life_models[model_id]
        model_usage["input_tokens"] = int(model_usage.get("input_tokens", 0)) + input_tokens
        model_usage["output_tokens"] = int(model_usage.get("output_tokens", 0)) + output_tokens
        model_usage["cost"] = float(model_usage.get("cost", 0.0)) + total_cost

        all_time = self.data.get("all_time_usage")
        if not isinstance(all_time, dict):
            all_time = self._new_all_time_usage()
            self.data["all_time_usage"] = all_time
        all_time = cast(AllTimeUsage, all_time)
        all_time["input_tokens"] = int(all_time["input_tokens"]) + input_tokens
        all_time["output_tokens"] = int(all_time["output_tokens"]) + output_tokens
        all_time["total_cost"] = float(all_time["total_cost"]) + total_cost

        # Add to history
        usage_history = self.data.get("usage_history")
        if not isinstance(usage_history, list):
            usage_history = []
            self.data["usage_history"] = usage_history
        usage_history = cast(list[UsageHistoryEntry], usage_history)
        usage_history.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": round(total_cost, 6),
            }
        )

        # Keep history manageable (last 100 transactions)
        if len(usage_history) > 100:
            self.data["usage_history"] = usage_history[-100:]

        self.save_if_changed(self.data)

        # Check status
        balance = float(self.data.get("current_balance_usd", 0.0) or 0.0)
        if balance <= 0:
            return "BANKRUPT"
        elif balance < 0.50:
            return "CRITICAL"
        elif balance < 1.00:
            return "LOW_BALANCE"
        else:
            return "OK"

    def get_balance(self) -> float:
        return float(self.data.get("current_balance_usd", 0.0) or 0.0)

    def get_status(self) -> dict[str, object]:
        self.data = self.ensure_usage_fields(self.data)
        balance = float(self.data.get("current_balance_usd", 0.0) or 0.0)
        monthly_spent = float(self.data.get("usage_monthly", 0.0) or 0.0)
        reset_date = datetime.fromisoformat(str(self.data.get("reset_date", "2000-01-01")))
        # Ensure reset_date is timezone-aware for comparison
        if reset_date.tzinfo is None:
            reset_date = reset_date.replace(tzinfo=timezone.utc)
        days_until_reset = (reset_date - datetime.now(timezone.utc)).days
        usage_history = self.data.get("usage_history", [])
        models_list, totals, _, _, _ = aggregate_usage(cast(UsageHistorySequence, usage_history))

        current_life_usage = self.data.get("current_life_usage")
        if not isinstance(current_life_usage, dict):
            current_life_usage = {}
        current_life_number_raw = current_life_usage.get("life_number", self.data.get("current_life_number", 0))
        try:
            current_life_number = int(current_life_number_raw or 0)
        except (TypeError, ValueError):
            current_life_number = 0
        current_life_input = int(current_life_usage.get("input_tokens", 0) or 0)
        current_life_output = int(current_life_usage.get("output_tokens", 0) or 0)
        current_life_cost = float(current_life_usage.get("total_cost", 0.0) or 0.0)

        all_time_usage = self.data.get("all_time_usage")
        if not isinstance(all_time_usage, dict):
            all_time_usage = {}
        all_time_input = int(all_time_usage.get("input_tokens", 0) or 0)
        all_time_output = int(all_time_usage.get("output_tokens", 0) or 0)
        all_time_cost = float(all_time_usage.get("total_cost", 0.0) or 0.0)

        remaining_percent = round((balance / self.monthly_budget) * 100, 1) if self.monthly_budget else 0.0
        result = {
            "balance": round(balance, 2),
            "budget": self.monthly_budget,
            "spent_this_month": round(monthly_spent, 2),
            "remaining_percent": remaining_percent,
            "days_until_reset": days_until_reset,
            "reset_date": reset_date.strftime("%Y-%m-%d"),
            "status": self.get_status_level(),
            "lives": self.get_lives(),
            "top_models": self.get_top_models(),
            "current_life": {
                "life_number": int(current_life_number),
                "total_input_tokens": current_life_input,
                "total_output_tokens": current_life_output,
                "total_tokens": current_life_input + current_life_output,
                "total_cost": round(current_life_cost, 6),
            },
            "all_time": {
                "total_input_tokens": all_time_input,
                "total_output_tokens": all_time_output,
                "total_tokens": all_time_input + all_time_output,
                "total_cost": round(all_time_cost, 6),
                "total_lives": self.get_lives(),
            },
            "models": models_list,
            "totals": totals,
        }
        return result

    def get_status_level(self) -> str:
        balance = float(self.data.get("current_balance_usd", 0.0) or 0.0)
        if balance <= 0:
            return "bankrupt"
        elif balance < 0.50:
            return "critical"
        elif balance < 1.00:
            return "cautious"
        elif balance < 3.00:
            return "moderate"
        else:
            return "comfortable"

    def get_top_models(self, limit: int = 5) -> list[TopModelEntry]:
        usage_by_model = cast(ModelCostEntry, self.data.get("usage_by_model", {}))
        models: list[TopModelEntry] = []
        for model_id, cost in usage_by_model.items():
            models.append({"model": model_id, "cost": round(float(cost or 0.0), 3)})

        models.sort(key=lambda item: item["cost"], reverse=True)
        return models[:limit]

    def can_afford(self, estimated_tokens: int, cost_per_1m: float) -> bool:
        estimated_cost = (estimated_tokens / 1_000_000) * cost_per_1m
        return float(self.data.get("current_balance_usd", 0.0) or 0.0) >= estimated_cost

    def get_token_budget(self, model_cost_per_1m: float) -> int:
        balance = float(self.data.get("current_balance_usd", 0.0) or 0.0)
        if balance <= 0:
            return 0

        tokens = int((balance / model_cost_per_1m) * 1_000_000)
        return tokens

    def save_data(self, data: CreditData) -> None:
        os.makedirs(os.path.dirname(CREDITS_FILE), exist_ok=True)
        with open(CREDITS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def save(self) -> None:
        self.save_data(self.data)

    def save_if_changed(self, data: CreditData) -> None:
        if data != self.data:
            self.save_data(data)
            self.data = data

    def increment_life(self) -> None:
        next_life = int(self.data.get("total_lives", 0) or 0) + 1
        self.start_life(next_life)

    def get_lives(self) -> int:
        return int(self.data.get("total_lives", 0) or 0)
