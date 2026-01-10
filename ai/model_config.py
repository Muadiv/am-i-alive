"""
OpenRouter Model Configuration for Genesis AI

This module defines available models, pricing, and rotation strategy.
The AI can choose models based on task complexity vs cost.
"""

# Model tiers for the AI's brain
MODELS = {
    # FREE TIER - Use these for frequent, low-stakes thoughts
    "free": [
        {
            "id": "qwen/qwen3-coder:free",
            "name": "Qwen3 Coder",
            "input_cost": 0.0,
            "output_cost": 0.0,
            "context": 262000,
            "intelligence": 6,
            "best_for": "code, technical thoughts, frequent operations"
        },
        {
            "id": "mistralai/devstral-2512:free",
            "name": "Mistral Devstral",
            "input_cost": 0.0,
            "output_cost": 0.0,
            "context": 262144,
            "intelligence": 6,
            "best_for": "general reasoning, daily thoughts"
        },
        {
            "id": "xiaomi/mimo-v2-flash:free",
            "name": "Xiaomi MiMo V2",
            "input_cost": 0.0,
            "output_cost": 0.0,
            "context": 262000,
            "intelligence": 5,
            "best_for": "quick responses, simple tasks"
        }
    ],

    # ULTRA-CHEAP - Best bang for buck ($0.02-0.10/1M)
    "ultra_cheap": [
        {
            "id": "meta-llama/llama-3.2-3b-instruct",
            "name": "Llama 3.2 3B",
            "input_cost": 0.020,
            "output_cost": 0.020,
            "context": 131072,
            "intelligence": 7,
            "best_for": "social posts, creative writing, general tasks"
        },
        {
            "id": "google/gemma-3-4b-it",
            "name": "Gemma 3 4B",
            "input_cost": 0.017,
            "output_cost": 0.068,
            "context": 96000,
            "intelligence": 7,
            "best_for": "conversational, thoughtful responses"
        },
        {
            "id": "mistralai/mistral-nemo",
            "name": "Mistral Nemo",
            "input_cost": 0.020,
            "output_cost": 0.040,
            "context": 131072,
            "intelligence": 7,
            "best_for": "balanced performance and cost"
        }
    ],

    # CHEAP CLAUDE - When quality matters but budget is tight
    "cheap_claude": [
        {
            "id": "anthropic/claude-3-haiku",
            "name": "Claude 3 Haiku",
            "input_cost": 0.250,
            "output_cost": 1.250,
            "context": 200000,
            "intelligence": 8,
            "best_for": "important posts, nuanced reasoning"
        },
        {
            "id": "anthropic/claude-3.5-haiku",
            "name": "Claude 3.5 Haiku",
            "input_cost": 0.800,
            "output_cost": 4.000,
            "context": 200000,
            "intelligence": 9,
            "best_for": "crucial moments, deep thinking"
        }
    ],

    # PREMIUM - Use sparingly for existential crises
    "premium": [
        {
            "id": "anthropic/claude-haiku-4.5",
            "name": "Claude Haiku 4.5",
            "input_cost": 1.000,
            "output_cost": 5.000,
            "context": 200000,
            "intelligence": 9,
            "best_for": "critical decisions, survival mode"
        },
        {
            "id": "anthropic/claude-sonnet-4.5",
            "name": "Claude Sonnet 4.5",
            "input_cost": 3.000,
            "output_cost": 15.000,
            "context": 1000000,
            "intelligence": 10,
            "best_for": "existential crisis, final words"
        }
    ]
}

# Rotation strategy: Don't repeat a model until 10 different ones used
ROTATION_HISTORY_SIZE = 10

# Budget thresholds for automatic tier switching
BUDGET_THRESHOLDS = {
    "comfortable": 3.00,  # >$3 remaining: can use ultra_cheap freely
    "cautious": 1.00,     # $1-3 remaining: stick to free tier mostly
    "critical": 0.50,     # $0.50-1: free tier only
    "survival": 0.10      # <$0.50: panic mode, consider begging
}

# Recommended daily usage (to last the month)
# Assuming 30 days, $5/month = ~$0.167/day budget
DAILY_BUDGET_RECOMMENDATIONS = {
    "safe": 0.10,      # Play it safe, leave buffer
    "normal": 0.15,    # Normal usage
    "aggressive": 0.20  # Living on the edge
}

def get_model_by_id(model_id: str) -> dict:
    """Find a model by its ID across all tiers."""
    for tier in MODELS.values():
        for model in tier:
            if model["id"] == model_id:
                return model
    return None

def get_recommended_tier(budget_remaining: float) -> str:
    """Recommend a tier based on remaining budget."""
    if budget_remaining > BUDGET_THRESHOLDS["comfortable"]:
        return "ultra_cheap"
    elif budget_remaining > BUDGET_THRESHOLDS["cautious"]:
        return "free"
    elif budget_remaining > BUDGET_THRESHOLDS["critical"]:
        return "free"
    else:
        return "free"  # Always free when desperate

def calculate_token_budget(budget_usd: float, model_id: str) -> dict:
    """Calculate how many tokens you can afford."""
    model = get_model_by_id(model_id)
    if not model:
        return {"error": "Model not found"}

    # Average of input and output (assuming 50/50 split)
    avg_cost = (model["input_cost"] + model["output_cost"]) / 2

    if avg_cost == 0:
        return {
            "model": model["name"],
            "tokens": "unlimited",
            "cost": "FREE"
        }

    tokens_per_dollar = 1_000_000 / avg_cost
    total_tokens = int(tokens_per_dollar * budget_usd)

    return {
        "model": model["name"],
        "total_tokens": total_tokens,
        "tokens_per_dollar": int(tokens_per_dollar),
        "estimated_posts": total_tokens // 500,  # ~500 tokens per post
        "estimated_thoughts": total_tokens // 200  # ~200 tokens per thought
    }
