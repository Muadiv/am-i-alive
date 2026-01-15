"""
Simple HTTP server to expose budget data to Observer.
Runs in a separate thread to not block the main AI loop.
"""

import json
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

CREDITS_FILE = "/app/credits/balance.json"


class BudgetHandler(BaseHTTPRequestHandler):
    """HTTP handler for budget endpoint."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/budget":
            try:
                # Load budget data
                with open(CREDITS_FILE, 'r') as f:
                    data = json.load(f)

                # Calculate derived stats
                total_tokens = sum(entry.get('total_tokens', 0) for entry in data.get('usage_history', []))
                budget = data.get('monthly_budget_usd', 5.0)
                balance = data.get('current_balance_usd', budget)
                spent = budget - balance
                remaining_percent = (balance / budget * 100) if budget > 0 else 0

                # Determine status
                if remaining_percent > 75:
                    status = "comfortable"
                elif remaining_percent > 50:
                    status = "moderate"
                elif remaining_percent > 25:
                    status = "cautious"
                elif remaining_percent > 0:
                    status = "critical"
                else:
                    status = "bankrupt"

                # Calculate days until reset
                try:
                    reset_date = datetime.fromisoformat(data.get('reset_date', '2000-01-01'))
                    days_until_reset = max(0, (reset_date - datetime.now(timezone.utc)).days)
                except:
                    days_until_reset = 0

                # Get top models by spending
                usage_by_model = data.get('usage_by_model', {})
                top_models = [
                    {"model": model, "cost": cost}
                    for model, cost in sorted(usage_by_model.items(), key=lambda x: x[1], reverse=True)[:5]
                ]

                # BE-002: Aggregate token usage by model for detailed reporting
                usage_history = data.get('usage_history', [])
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
                    model_total_tokens = stats["input_tokens"] + stats["output_tokens"]
                    models_list.append({
                        "model": model_id,
                        "input_tokens": stats["input_tokens"],
                        "output_tokens": stats["output_tokens"],
                        "total_tokens": model_total_tokens,
                        "cost": round(stats["cost"], 6)
                    })

                models_list.sort(key=lambda item: item["total_tokens"], reverse=True)

                # Calculate ALL-TIME totals (entire project history)
                all_time_input = 0
                all_time_output = 0
                all_time_cost = 0.0

                for entry in usage_history:
                    all_time_input += int(entry.get('input_tokens', 0) or 0)
                    all_time_output += int(entry.get('output_tokens', 0) or 0)
                    all_time_cost += float(entry.get('cost_usd', 0) or 0)

                # Build response
                response_data = {
                    "budget": budget,
                    "balance": balance,
                    "spent_this_month": spent,
                    "remaining_percent": remaining_percent,
                    "status": status,
                    "reset_date": data.get('reset_date', 'unknown'),
                    "days_until_reset": days_until_reset,
                    "lives": data.get('total_lives', 0),
                    "total_tokens": total_tokens,
                    "top_models": top_models,
                    "models": models_list,  # BE-002: Detailed token breakdown
                    "totals": {  # BE-002: Total token usage summary (CURRENT CONTEXT - last 100 calls)
                        "total_input_tokens": total_input_tokens,
                        "total_output_tokens": total_output_tokens,
                        "total_tokens": total_input_tokens + total_output_tokens,
                        "total_cost": round(total_cost, 6)
                    },
                    "all_time": {  # All-time totals across entire project
                        "total_input_tokens": all_time_input,
                        "total_output_tokens": all_time_output,
                        "total_tokens": all_time_input + all_time_output,
                        "total_cost": round(all_time_cost, 6),
                        "total_lives": data.get('total_lives', 0)
                    },
                    "error": False
                }

                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())

            except Exception as e:
                # Send error response
                error_response = {
                    "error": True,
                    "details": str(e),
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
