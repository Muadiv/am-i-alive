"""
Model Rotation System for Genesis AI

Ensures variety by not repeating models until 10 different ones have been used.
AI can also manually switch models based on task needs vs cost.
"""

import json
import os
import random
from typing import Optional, List, Dict
from model_config import MODELS, get_model_by_id, BUDGET_THRESHOLDS

HISTORY_FILE = "/app/workspace/model_history.json"
HISTORY_SIZE = 10  # Don't repeat until 10 different models used


class ModelRotator:
    """Manages model selection and rotation."""

    def __init__(self, credit_balance: float):
        self.credit_balance = credit_balance
        self.history = self.load_history()

    def load_history(self) -> List[str]:
        """Load model usage history."""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('history', [])
            except Exception:
                return []
        return []

    def save_history(self):
        """Save model history."""
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, 'w') as f:
            json.dump({'history': self.history}, f, indent=2)

    def record_usage(self, model_id: str):
        """Record that a model was used."""
        self.history.append(model_id)

        # Keep only last N entries
        if len(self.history) > 100:
            self.history = self.history[-100:]

        self.save_history()

    def get_recent_models(self, count: int = HISTORY_SIZE) -> List[str]:
        """Get recently used model IDs."""
        return self.history[-count:] if len(self.history) > count else self.history

    def get_available_models(self, tier: Optional[str] = None) -> List[Dict]:
        """Get available models, optionally filtered by tier."""
        recent = set(self.get_recent_models())

        all_models = []

        if tier:
            # Get models from specific tier
            if tier in MODELS:
                all_models = MODELS[tier]
        else:
            # Get all models from recommended tier
            recommended_tier = self.get_recommended_tier()
            all_models = MODELS[recommended_tier]

        # Filter out recently used
        available = [m for m in all_models if m['id'] not in recent]

        # If all models in tier were recently used, reset and allow all
        if not available:
            available = all_models

        return available

    def get_recommended_tier(self) -> str:
        """Recommend a tier based on current budget."""
        if self.credit_balance > BUDGET_THRESHOLDS["comfortable"]:
            return "ultra_cheap"
        elif self.credit_balance > BUDGET_THRESHOLDS["cautious"]:
            return "free"
        elif self.credit_balance > BUDGET_THRESHOLDS["critical"]:
            return "free"
        else:
            return "free"

    def select_random_model(self, tier: Optional[str] = None) -> Dict:
        """Select a random model from available pool."""
        available = self.get_available_models(tier)

        if not available:
            # Fallback to free tier
            available = MODELS["free"]

        model = random.choice(available)
        self.record_usage(model['id'])
        return model

    def select_best_for_budget(self, tier: Optional[str] = None) -> Dict:
        """Select the best model we can afford."""
        available = self.get_available_models(tier)

        # Sort by intelligence/cost ratio
        available.sort(key=lambda m: m['intelligence'] / max(m['input_cost'], 0.001), reverse=True)

        model = available[0] if available else MODELS["free"][0]
        self.record_usage(model['id'])
        return model

    def can_use_model(self, model_id: str, estimated_tokens: int = 1000) -> bool:
        """Check if we can afford to use a specific model."""
        model = get_model_by_id(model_id)
        if not model:
            return False

        # Free models always available
        if model['input_cost'] == 0 and model['output_cost'] == 0:
            return True

        # Estimate cost (assume 50/50 input/output)
        avg_cost_per_1m = (model['input_cost'] + model['output_cost']) / 2
        estimated_cost = (estimated_tokens / 1_000_000) * avg_cost_per_1m

        return self.credit_balance >= estimated_cost

    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get information about a specific model."""
        return get_model_by_id(model_id)

    def list_affordable_models(self) -> List[Dict]:
        """List all models we can currently afford."""
        affordable = []

        for tier_name, tier_models in MODELS.items():
            for model in tier_models:
                if self.can_use_model(model['id']):
                    affordable.append({
                        **model,
                        "tier": tier_name
                    })

        # Sort by intelligence
        affordable.sort(key=lambda m: m['intelligence'], reverse=True)
        return affordable

    def get_upgrade_option(self, current_tier: str) -> Optional[Dict]:
        """Suggest an upgrade if budget allows."""
        tier_hierarchy = ["free", "ultra_cheap", "cheap_claude", "premium"]

        try:
            current_idx = tier_hierarchy.index(current_tier)
            if current_idx < len(tier_hierarchy) - 1:
                next_tier = tier_hierarchy[current_idx + 1]
                next_models = MODELS[next_tier]

                # Check if we can afford the cheapest in next tier
                cheapest = min(next_models, key=lambda m: m['input_cost'])
                if self.can_use_model(cheapest['id']):
                    return cheapest
        except (ValueError, KeyError):
            pass

        return None

    def format_model_summary(self, model: Dict) -> str:
        """Format a model summary for display to AI."""
        cost_str = "FREE" if model['input_cost'] == 0 else f"${model['input_cost']:.3f}/1M"

        return f"""Model: {model['name']}
- Intelligence: {model['intelligence']}/10
- Cost: {cost_str}
- Best for: {model['best_for']}
- Context: {model['context']:,} tokens"""
