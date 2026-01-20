from typing import Dict, List, Tuple


def aggregate_usage(usage_history: List[Dict]) -> Tuple[List[Dict], Dict, int, int, float]:
    models: Dict[str, Dict[str, float]] = {}
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

    totals = {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "total_cost": round(total_cost, 6)
    }

    return models_list, totals, total_input_tokens, total_output_tokens, total_cost
