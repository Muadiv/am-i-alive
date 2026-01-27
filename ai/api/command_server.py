"""
AI Command Server - Handles internal HTTP API requests from Observer.

Responsible for:
- Birth notification
- Force sync
- Health check
- Shutdown
"""

import asyncio
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from ..brain import INTERNAL_API_KEY, AIBrain
from ..logging_config import logger

# Globals for command server
_brain: AIBrain | None = None
_birth_event: asyncio.Event | None = None
_pending_birth_data: dict[str, Any] | None = None


def validate_internal_key(handler: BaseHTTPRequestHandler) -> bool:
    """Validate X-Internal-Key header for secure internal API access."""
    if not INTERNAL_API_KEY:
        logger.warning("Internal API key not configured")
        return False
    return handler.headers.get("x-internal-key") == INTERNAL_API_KEY


class CommandRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests to the AI command server."""

    def _send_response(self, status: int, data: str):
        """Send HTTP response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Internal-Key")
        self.end_headers()
        self.wfile.write(data.encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight OPTIONS request."""
        self._send_response(200, "{}")

    def do_GET(self):
        """Handle GET requests - health check."""
        if self.path == "/health":
            self._send_response(200, '{"status": "ok"}')
        elif self.path == "/state":
            self._send_response(200, json.dumps(get_current_state()))
        else:
            self._send_response(404, '{"error": "Not found"}')

    def do_POST(self):
        """Handle POST requests."""
        try:
            if self.path == "/birth":
                self._handle_birth()
            elif self.path == "/force-sync":
                self._handle_force_sync()
            elif self.path == "/shutdown":
                self._handle_shutdown()
            else:
                self._send_response(404, '{"error": "Not found"}')
        except Exception as e:
            logger.error(f"Error handling {self.path}: {e}")
            self._send_response(500, json.dumps({"error": str(e)}))

    def _handle_birth(self):
        """Handle birth notification from Observer."""
        global _pending_birth_data, _birth_event

        if not validate_internal_key(self):
            self._send_response(401, '{"error": "Unauthorized"}')
            return

        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length))

        logger.info(f"Birth notification received: {data}")

        # Signal to birth sequence
        _pending_birth_data = data
        if _birth_event:
            _birth_event.set()

        self._send_response(200, '{"status": "ok"}')

    def _handle_force_sync(self):
        """Handle force sync from Observer."""
        global _pending_birth_data, _birth_event

        if not validate_internal_key(self):
            self._send_response(401, '{"error": "Unauthorized"}')
            return

        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length))

        logger.info(f"Force sync request received: {data}")

        _pending_birth_data = data
        if _birth_event:
            _birth_event.set()

        self._send_response(200, '{"status": "ok"}')

    def _handle_shutdown(self):
        """Handle shutdown command from Observer."""
        if not validate_internal_key(self):
            self._send_response(401, '{"error": "Unauthorized"}')
            return

        logger.warning("Shutdown command received")
        self._send_response(200, '{"status": "ok"}')
        # Schedule shutdown
        asyncio.get_event_loop().call_soon(sys.exit, 0)


def get_current_state() -> dict:
    """Get current AI state for Observer sync validation."""
    if not _brain:
        return {"life_number": 0, "is_alive": False}

    return {
        "life_number": _brain.life_number,
        "is_alive": _brain.is_alive,
        "model": _brain.current_model.get("name") if _brain.current_model else None,
        "tokens_used": _brain.tokens_used_life,
    }


async def start_command_server(port: int, brain: AIBrain, birth_event: asyncio.Event) -> None:
    """Start the HTTP command server."""
    global _brain, _birth_event
    _brain = brain
    _birth_event = birth_event

    logger.info(f"Starting command server on :{port}")

    def run_server():
        with HTTPServer(("", port), CommandRequestHandler) as httpd:
            httpd.serve_forever()

    # Run server in separate thread
    import threading

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
