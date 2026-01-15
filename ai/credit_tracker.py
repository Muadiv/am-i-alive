"""
Credit Tracking System for Genesis AI

Tracks OpenRouter API usage, manages budget, and prevents bankruptcy.
The credit balance SURVIVES DEATH - it's part of the meta-game.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

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
                    self.save_data(data)

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
            "usage_monthly": 0,
            "usage_by_model": {},
            "usage_history": []
        }
        self.save_data(data)
        return data

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

        # Deduct from balance
        self.data['current_balance_usd'] -= total_cost
        self.data['usage_monthly'] += total_cost

        # Track by model
        if model_id not in self.data['usage_by_model']:
            self.data['usage_by_model'][model_id] = 0
        self.data['usage_by_model'][model_id] += total_cost

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

        self.save_data(self.data)

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
        balance = self.data['current_balance_usd']
        monthly_spent = self.data['usage_monthly']
        reset_date = datetime.fromisoformat(self.data['reset_date'])
        # Ensure reset_date is timezone-aware for comparison
        if reset_date.tzinfo is None:
            reset_date = reset_date.replace(tzinfo=timezone.utc)
        days_until_reset = (reset_date - datetime.now(timezone.utc)).days
        # BE-002: Aggregate token usage by model for detailed reporting
        usage_history = self.data.get('usage_history', [])
        models = {}
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0

        for entry in usage_history:
            model_id = entry.get('model', 'unknown')
            input_tokens = int(entry.get('input_tokens', 0) or 0)
            output_tokens = int(entry.get('output_tokens', 0) or 0)
            cost_usd = float(entry.get('cost_usd', 0) or 0)

            if model_id not in models:
                models[model_id] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0
                }

            models[model_id]["input_tokens"] += input_tokens
            models[model_id]["output_tokens"] += output_tokens
            models[model_id]["cost"] += cost_usd

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_cost += cost_usd

        models_list = []
        for model_id, stats in models.items():
            total_tokens = stats["input_tokens"] + stats["output_tokens"]
            models_list.append({
                "model": model_id,
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
                "total_tokens": total_tokens,
                "cost": round(stats["cost"], 6)
            })

        models_list.sort(key=lambda item: item["total_tokens"], reverse=True)

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
            # BE-002: Detailed token usage for budget dashboard
            "models": models_list,
            "totals": {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "total_cost": round(total_cost, 6)
            }
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

    def increment_life(self):
        """Increment life counter (called on respawn)."""
        self.data['total_lives'] += 1
        self.save()

    def get_lives(self) -> int:
        """Get total lives lived."""
        return self.data.get('total_lives', 0)
