import logging
import threading
import time
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI

from .budget_aggregator import aggregate_usage  # type: ignore
from .credit_tracker import CreditTracker  # type: ignore
from .logging_config import logger

_cache_lock = threading.Lock()
_cached_payload: dict[str, object] | None = None
_cached_at: datetime | None = None
_cache_ttl_seconds = 5
_credit_tracker = CreditTracker()

app = FastAPI()


def _build_response() -> dict[str, object]:
    data = _credit_tracker.get_status()
    usage_history = _credit_tracker.data.get("usage_history", [])
    if not isinstance(usage_history, list):
        usage_history = []
    models, totals, _, _, _ = aggregate_usage(usage_history)

    response_data: dict[str, object] = {
        "budget": data.get("budget") or data.get("monthly_budget_usd", 5.0),
        "balance": data.get("balance") or data.get("current_balance_usd", 0.0),
        "spent_this_month": data.get("spent_this_month", 0.0),
        "remaining_percent": data.get("remaining_percent", 0.0),
        "status": data.get("status", "unknown"),
        "reset_date": data.get("reset_date", "unknown"),
        "days_until_reset": data.get("days_until_reset", 0),
        "lives": data.get("lives") or data.get("total_lives", 0),
        "total_tokens": totals.get("total_tokens", 0),
        "top_models": data.get("top_models", []),
        "models": models,
        "totals": totals,
        "current_life": data.get("current_life", {}),
        "all_time": data.get("all_time", {}),
        "error": False,
    }
    return response_data


def _get_cached_response() -> dict[str, object]:
    global _cached_payload, _cached_at
    now = datetime.now(timezone.utc)
    with _cache_lock:
        if _cached_payload is not None and _cached_at is not None:
            age = (now - _cached_at).total_seconds()
            if age < _cache_ttl_seconds:
                return _cached_payload

    response_data = _build_response()
    with _cache_lock:
        _cached_payload = response_data
        _cached_at = now
    return response_data


@app.get("/budget")
async def budget():
    return _get_cached_response()


@app.get("/health")
async def health():
    """Health check endpoint for the budget server."""
    try:
        # Check if credit tracker is accessible
        status = _credit_tracker.get_status()
        return {
            "status": "ok",
            "service": "budget-server",
            "balance": status.get("balance"),
            "remaining_percent": status.get("remaining_percent"),
            "days_until_reset": status.get("days_until_reset"),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "service": "budget-server", "error": str(e)}, 500


def start_budget_server(port: int = 8000) -> uvicorn.Server:
    server_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(server_config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


if __name__ == "__main__":
    _server = start_budget_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
