"""
Model Rotation System for Genesis AI

Ensures variety by not repeating models until 10 different ones have been used.
AI can also manually switch models based on task needs vs cost.
"""

import json
import os
import random
from typing import Dict, List, Optional

from .logging_config import logger
from .model_config import (
    BUDGET_THRESHOLDS,
    MODELS,
    TIER_ORDER,
    get_model_by_id,
    get_tier_for_model,
    list_paid_models_by_cost,
)

HISTORY_FILE = "/app/workspace/model_history.json"
HISTORY_SIZE = 10  # Don't repeat until 10 different models used


class ModelRotator:
    """Manages model selection and rotation."""

    def __init__(self, credit_balance: float):
        self.credit_balance = credit_balance
        self.history = self.load_history()
        self.free_failure_counts: Dict[str, int] = {}

    def load_history(self) -> List[str]:
        """Load model usage history."""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    history = data.get("history", [])
                    if isinstance(history, list):
                        filtered = [model_id for model_id in history if get_model_by_id(str(model_id))]
                        if len(filtered) != len(history):
                            logger.warning("[MODEL] ⚠️ Removed unknown models from history")
                            self.history = filtered
                            self.save_history()
                        return filtered
                    return []
            except Exception as e:
                logger.warning(f"[MODEL] ⚠️ Failed to load model history: {e}")
                return []
        return []

    def save_history(self):
        """Save model history."""
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump({"history": self.history}, f, indent=2)

    def record_usage(self, model_id: str):
        """Record that a model was used."""
        self.history.append(model_id)

        # Keep only last N entries
        if len(self.history) > 100:
            self.history = self.history[-100:]

        self.save_history()

    def record_free_failure(self, model_id: str) -> int:
        """Record a failure for a free model and return current failure count."""
        current = self.free_failure_counts.get(model_id, 0) + 1
        self.free_failure_counts[model_id] = current
        return current

    def reset_free_failure(self, model_id: str) -> None:
        """Reset failure count for a model after a successful call."""
        if model_id in self.free_failure_counts:
            del self.free_failure_counts[model_id]

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
        available = [m for m in all_models if m["id"] not in recent]

        # If all models in tier were recently used, reset and allow all
        if not available:
            available = all_models

        return available

    def get_next_paid_model(self, current_model_id: Optional[str] = None) -> Optional[Dict]:
        """Pick the cheapest paid model, upgrading gently based on history and current tier."""
        paid_models = list_paid_models_by_cost()
        if not paid_models:
            return None

        if not current_model_id:
            model = paid_models[0]
            self.record_usage(model["id"])
            return model

        current_tier = get_tier_for_model(current_model_id) or "free"
        if current_tier not in TIER_ORDER:
            current_tier = "free"

        start_index = 0
        if current_tier in TIER_ORDER and current_tier != "free":
            current_index = TIER_ORDER.index(current_tier)
            for idx, model in enumerate(paid_models):
                model_tier = get_tier_for_model(model["id"])
                if model_tier and TIER_ORDER.index(model_tier) >= current_index:
                    start_index = idx
                    break

        selection = paid_models[start_index]
        self.record_usage(selection["id"])
        return selection

    def get_recommended_tier(self) -> str:
        """Recommend a tier based on current budget."""
        if self.credit_balance > 0:
            return "ultra_cheap"
        return "ultra_cheap"

    def select_random_model(self, tier: Optional[str] = None) -> Dict:
        """Select a random model from available pool."""
        available = self.get_available_models(tier)

        if not available:
            available = MODELS["ultra_cheap"]

        model = random.choice(available)
        self.record_usage(model["id"])
        return model

    def select_best_for_budget(self, tier: Optional[str] = None) -> Dict:
        """Select the best model we can afford."""
        available = self.get_available_models(tier)

        # Sort by intelligence/cost ratio
        available.sort(key=lambda m: m["intelligence"] / max(m["input_cost"], 0.001), reverse=True)

        model = available[0] if available else MODELS["ultra_cheap"][0]
        self.record_usage(model["id"])
        return model

    def can_use_model(self, model_id: str, estimated_tokens: int = 1000) -> bool:
        """Check if we can afford to use a specific model."""
        model = get_model_by_id(model_id)
        if not model:
            return False

        # Free models always available
        if model["input_cost"] == 0 and model["output_cost"] == 0:
            return True

        # Estimate cost (assume 50/50 input/output)
        avg_cost_per_1m = (model["input_cost"] + model["output_cost"]) / 2
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
                if self.can_use_model(model["id"]):
                    affordable.append({**model, "tier": tier_name})

        # Sort by intelligence
        affordable.sort(key=lambda m: m["intelligence"], reverse=True)
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
                cheapest = min(next_models, key=lambda m: m["input_cost"])
                if self.can_use_model(cheapest["id"]):
                    return cheapest
        except (ValueError, KeyError):
            pass

        return None

    def format_model_summary(self, model: Dict) -> str:
        """Format a model summary for display to AI."""
        cost_str = "FREE" if model["input_cost"] == 0 else f"${model['input_cost']:.3f}/1M"

        return f"""Model: {model['name']}
- Intelligence: {model['intelligence']}/10
- Cost: {cost_str}
- Best for: {model['best_for']}
- Context: {model['context']:,} tokens"""
