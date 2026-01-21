from collections.abc import Sequence
from typing import TypedDict


class UsageEntry(TypedDict):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class ModelUsage(TypedDict):
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float


class Totals(TypedDict):
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float


def aggregate_usage(usage_history: Sequence[UsageEntry]) -> tuple[list[ModelUsage], Totals, int, int, float]:
    models: dict[str, dict[str, float]] = {}
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    for entry in usage_history:
        model_id = entry.get("model", "unknown")
        input_tokens = int(entry.get("input_tokens", 0) or 0)
        output_tokens = int(entry.get("output_tokens", 0) or 0)
        cost_usd = float(entry.get("cost_usd", 0) or 0)

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

    models_list: list[ModelUsage] = []
    for model_id, stats in models.items():
        input_tokens = int(stats["input_tokens"])
        output_tokens = int(stats["output_tokens"])
        total_tokens = input_tokens + output_tokens
        models_list.append({
            "model": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": round(stats["cost"], 6)
        })

    models_list.sort(key=lambda item: item["total_tokens"], reverse=True)

    totals: Totals = {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "total_cost": round(total_cost, 6)
    }

    return models_list, totals, total_input_tokens, total_output_tokens, total_cost
