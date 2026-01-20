"""
Simple HTTP server to expose budget data to Observer.
Runs in a separate thread to not block the main AI loop.
"""

import json
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

from credit_tracker import CreditTracker

CREDITS_FILE = "/app/credits/balance.json"

_cache_lock = threading.Lock()
_cached_payload = None
_cached_at = None
_cache_ttl_seconds = 5
_credit_tracker = CreditTracker()


class BudgetHandler(BaseHTTPRequestHandler):
    """HTTP handler for budget endpoint."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        global _cached_payload, _cached_at
        if self.path == "/budget":
            try:
                now = datetime.now(timezone.utc)
                with _cache_lock:
                    if _cached_payload and _cached_at:
                        age = (now - _cached_at).total_seconds()
                        if age < _cache_ttl_seconds:
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(_cached_payload).encode())
                            return

                data = _credit_tracker.get_status()

                response_data = {
                    "budget": data.get("budget", data.get("monthly_budget_usd", 5.0)),
                    "balance": data.get("balance", data.get("current_balance_usd", 0.0)),
                    "spent_this_month": data.get("spent_this_month", 0.0),
                    "remaining_percent": data.get("remaining_percent", 0.0),
                    "status": data.get("status", "unknown"),
                    "reset_date": data.get("reset_date", "unknown"),
                    "days_until_reset": data.get("days_until_reset", 0),
                    "lives": data.get("total_lives", data.get("total_lives", 0)),
                    "total_tokens": data.get("total_tokens", 0),
                    "top_models": data.get("top_models", []),
                    "models": data.get("models", []),
                    "totals": data.get("totals", {}),
                    "current_life": data.get("current_life", {}),
                    "all_time": data.get("all_time", {}),
                    "error": False
                }

                with _cache_lock:
                    _cached_payload = response_data
                    _cached_at = now

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())

            except Exception as e:
                print(f"[BUDGET_SERVER] ❌ Failed to build budget response: {e}")
                error_response = {
                    "error": True,
                    "details": "Internal server error",
                    "budget": 5.0,
                    "balance": 0,
                    "status": "unknown"
                }
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())

        elif self.path == "/health":
            # Health check endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

        else:
            # Not found
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())


def start_budget_server(port=8000):
    """Start the budget HTTP server in a separate thread."""
    server = HTTPServer(('0.0.0.0', port), BudgetHandler)
    print(f"[BUDGET_SERVER] 🌐 Starting budget server on port {port}...")

    # Run server in background thread
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"[BUDGET_SERVER] ✅ Budget server running on http://0.0.0.0:{port}")
    return server


if __name__ == "__main__":
    # For testing
    start_budget_server()
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
