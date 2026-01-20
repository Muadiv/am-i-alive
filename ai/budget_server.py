import threading
import time
from datetime import datetime, timezone

from fastapi import FastAPI
import uvicorn

from credit_tracker import CreditTracker


_cache_lock = threading.Lock()
_cached_payload = None
_cached_at = None
_cache_ttl_seconds = 5
_credit_tracker = CreditTracker()

app = FastAPI()


def _build_response() -> dict:
    data = _credit_tracker.get_status()
    totals = data.get("totals", {})
    response_data = {
        "budget": data.get("budget", data.get("monthly_budget_usd", 5.0)),
        "balance": data.get("balance", data.get("current_balance_usd", 0.0)),
        "spent_this_month": data.get("spent_this_month", 0.0),
        "remaining_percent": data.get("remaining_percent", 0.0),
        "status": data.get("status", "unknown"),
        "reset_date": data.get("reset_date", "unknown"),
        "days_until_reset": data.get("days_until_reset", 0),
        "lives": data.get("lives", data.get("total_lives", 0)),
        "total_tokens": totals.get("total_tokens", 0),
        "top_models": data.get("top_models", []),
        "models": data.get("models", []),
        "totals": totals,
        "current_life": data.get("current_life", {}),
        "all_time": data.get("all_time", {}),
        "error": False,
    }
    return response_data


def _get_cached_response() -> dict:
    global _cached_payload, _cached_at
    now = datetime.now(timezone.utc)
    with _cache_lock:
        if _cached_payload and _cached_at:
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
    return {"status": "ok"}


def start_budget_server(port=8000):
    server_config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(server_config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


if __name__ == "__main__":
    start_budget_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
