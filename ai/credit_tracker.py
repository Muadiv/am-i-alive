"""
Credit Tracking System for Genesis AI

Tracks OpenRouter API usage, manages budget, and prevents bankruptcy.
The credit balance SURVIVES DEATH - it's part of the meta-game.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from budget_aggregator import aggregate_usage

CREDITS_FILE = "/app/credits/balance.json"


class CreditTracker:
    """Manages the AI's token budget and spending."""

    def __init__(self, monthly_budget: float = 5.00):
        self.monthly_budget = monthly_budget
        self.data = self.load()

    def load(self) -> Dict:
        """Load credit data from persistent storage."""
        if os.path.exists(CREDITS_FILE):
            try:
                with open(CREDITS_FILE, 'r') as f:
                    data = json.load(f)

                # Check if we need to reset monthly budget
                reset_date = datetime.fromisoformat(data.get('reset_date', '2000-01-01'))
                # Ensure reset_date is timezone-aware for comparison
                if reset_date.tzinfo is None:
                    reset_date = reset_date.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) >= reset_date:
                    # Monthly reset!
                    print(f"[CREDITS] 🎉 Monthly budget reset! New balance: ${self.monthly_budget:.2f}")
                    data['current_balance_usd'] = self.monthly_budget
                    data['reset_date'] = self.get_next_reset_date()
                    data['usage_monthly'] = 0
                    self.save_if_changed(data)

                needs_save = False
                if "current_life_number" not in data:
                    needs_save = True
                current_life = data.get("current_life_usage")
                if not isinstance(current_life, dict):
                    needs_save = True
                else:
                    for key in ("life_number", "input_tokens", "output_tokens", "total_cost", "models"):
                        if key not in current_life:
                            needs_save = True
                            break

                all_time = data.get("all_time_usage")
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
                print(f"[CREDITS] Error loading credits file: {e}")
                return self.create_new_data()
        else:
            return self.create_new_data()

    def create_new_data(self) -> Dict:
        """Create initial credit data structure."""
        data = {
            "monthly_budget_usd": self.monthly_budget,
            "current_balance_usd": self.monthly_budget,
            "reset_date": self.get_next_reset_date(),
            "total_lives": 0,
            "current_life_number": 0,
            "current_life_usage": self._new_life_usage(0),
            "all_time_usage": self._new_all_time_usage(),
            "usage_monthly": 0,
            "usage_by_model": {},
            "usage_history": []
        }
        self.save_data(data)
        return data

    def _new_life_usage(self, life_number: int) -> Dict:
        return {
            "life_number": int(life_number),
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0.0,
            "models": {}
        }

    def _new_all_time_usage(self) -> Dict:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0.0
        }

    def ensure_usage_fields(self, data: Dict) -> Dict:
        if "current_life_number" not in data:
            data["current_life_number"] = data.get("total_lives", 0)

        life_number = data.get("current_life_number", 0) or 0
        current_life = data.get("current_life_usage")
        if not isinstance(current_life, dict):
            current_life = self._new_life_usage(life_number)
            data["current_life_usage"] = current_life

        current_life.setdefault("life_number", int(life_number))
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

    def start_life(self, life_number: int):
        try:
            life_number = int(life_number)
        except (TypeError, ValueError):
            life_number = 0

        self.data = self.ensure_usage_fields(self.data)
        self.data["current_life_number"] = life_number
        self.data["current_life_usage"] = self._new_life_usage(life_number)
        if life_number > self.data.get("total_lives", 0):
            self.data["total_lives"] = life_number
        self.save()

    def get_next_reset_date(self) -> str:
        """Calculate next monthly reset date."""
        now = datetime.now(timezone.utc)
        # Reset on the 1st of next month (timezone-aware)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        return next_month.isoformat()

    def charge(self, model_id: str, input_tokens: int, output_tokens: int,
               input_cost_per_1m: float, output_cost_per_1m: float) -> str:
        """
        Charge for API usage.

        Returns: "OK", "LOW_BALANCE", or "BANKRUPT"
        """
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
        total_cost = input_cost + output_cost

        self.data = self.ensure_usage_fields(self.data)
        current_life = self.data["current_life_usage"]
        if current_life.get("life_number") != self.data.get("current_life_number", 0):
            current_life = self._new_life_usage(self.data.get("current_life_number", 0))
            self.data["current_life_usage"] = current_life

        # Deduct from balance
        self.data['current_balance_usd'] -= total_cost
        self.data['usage_monthly'] += total_cost

        # Track by model
        if model_id not in self.data['usage_by_model']:
            self.data['usage_by_model'][model_id] = 0
        self.data['usage_by_model'][model_id] += total_cost

        current_life["input_tokens"] += input_tokens
        current_life["output_tokens"] += output_tokens
        current_life["total_cost"] += total_cost
        life_models = current_life["models"]
        if model_id not in life_models:
            life_models[model_id] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
        life_models[model_id]["input_tokens"] += input_tokens
        life_models[model_id]["output_tokens"] += output_tokens
        life_models[model_id]["cost"] += total_cost

        all_time = self.data["all_time_usage"]
        all_time["input_tokens"] += input_tokens
        all_time["output_tokens"] += output_tokens
        all_time["total_cost"] += total_cost

        # Add to history
        self.data['usage_history'].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(total_cost, 6)
        })

        # Keep history manageable (last 100 transactions)
        if len(self.data['usage_history']) > 100:
            self.data['usage_history'] = self.data['usage_history'][-100:]

        self.save_if_changed(self.data)

        # Check status
        balance = self.data['current_balance_usd']
        if balance <= 0:
            return "BANKRUPT"
        elif balance < 0.50:
            return "CRITICAL"
        elif balance < 1.00:
            return "LOW_BALANCE"
        else:
            return "OK"

    def get_balance(self) -> float:
        """Get current balance."""
        return self.data['current_balance_usd']

    def get_status(self) -> Dict:
        """Get full status information."""
        self.data = self.ensure_usage_fields(self.data)
        balance = self.data['current_balance_usd']
        monthly_spent = self.data['usage_monthly']
        reset_date = datetime.fromisoformat(self.data['reset_date'])
        # Ensure reset_date is timezone-aware for comparison
        if reset_date.tzinfo is None:
            reset_date = reset_date.replace(tzinfo=timezone.utc)
        days_until_reset = (reset_date - datetime.now(timezone.utc)).days
        usage_history = self.data.get('usage_history', [])
        models_list, totals, total_input_tokens, total_output_tokens, total_cost = aggregate_usage(usage_history)

        current_life_usage = self.data.get("current_life_usage", {})
        current_life_number = current_life_usage.get(
            "life_number",
            self.data.get("current_life_number", 0)
        )
        current_life_input = int(current_life_usage.get("input_tokens", 0) or 0)
        current_life_output = int(current_life_usage.get("output_tokens", 0) or 0)
        current_life_cost = float(current_life_usage.get("total_cost", 0.0) or 0.0)

        all_time_usage = self.data.get("all_time_usage", {})
        all_time_input = int(all_time_usage.get("input_tokens", 0) or 0)
        all_time_output = int(all_time_usage.get("output_tokens", 0) or 0)
        all_time_cost = float(all_time_usage.get("total_cost", 0.0) or 0.0)

        return {
            "balance": round(balance, 2),
            "budget": self.monthly_budget,
            "spent_this_month": round(monthly_spent, 2),
            "remaining_percent": round((balance / self.monthly_budget) * 100, 1),
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
                "total_cost": round(current_life_cost, 6)
            },
            "all_time": {
                "total_input_tokens": all_time_input,
                "total_output_tokens": all_time_output,
                "total_tokens": all_time_input + all_time_output,
                "total_cost": round(all_time_cost, 6),
                "total_lives": self.get_lives()
            },
            # BE-002: Detailed token usage for budget dashboard
            "models": models_list,
            "totals": totals
        }

    def get_status_level(self) -> str:
        """Get status level: comfortable, cautious, critical, or bankrupt."""
        balance = self.data['current_balance_usd']
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

    def get_top_models(self, limit: int = 5) -> list:
        """Get top models by spending."""
        models = []
        for model_id, cost in self.data['usage_by_model'].items():
            models.append({"model": model_id, "cost": round(cost, 3)})

        models.sort(key=lambda x: x['cost'], reverse=True)
        return models[:limit]

    def can_afford(self, estimated_tokens: int, cost_per_1m: float) -> bool:
        """Check if we can afford an operation."""
        estimated_cost = (estimated_tokens / 1_000_000) * cost_per_1m
        return self.data['current_balance_usd'] >= estimated_cost

    def get_token_budget(self, model_cost_per_1m: float) -> int:
        """Calculate how many tokens we can still afford."""
        balance = self.data['current_balance_usd']
        if balance <= 0:
            return 0

        tokens = int((balance / model_cost_per_1m) * 1_000_000)
        return tokens

    def save_data(self, data: Dict):
        """Save credit data to persistent storage."""
        os.makedirs(os.path.dirname(CREDITS_FILE), exist_ok=True)
        with open(CREDITS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def save(self):
        """Save current data."""
        self.save_data(self.data)

    def save_if_changed(self, data: Dict):
        if data != self.data:
            self.save_data(data)
            self.data = data

    def increment_life(self):
        """Increment life counter (called on respawn)."""
        next_life = self.data.get("total_lives", 0) + 1
        self.start_life(next_life)

    def get_lives(self) -> int:
        """Get total lives lived."""
        return self.data.get('total_lives', 0)
