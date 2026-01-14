#!/usr/bin/env python3
"""
Telegram AI Bridge - Remote Command System for Am I Alive

Allows the creator to send commands to Claude Code from Telegram when away from home.
Falls back to Codex or Gemini if Claude is unavailable.
Only the whitelisted user can send commands.

Security:
- User ID whitelist via TELEGRAM_AUTHORIZED_USER_ID
- Commands are logged
- Only executes in am-i-alive project directory
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
import requests
import shutil
import random

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = os.getenv("TELEGRAM_AUTHORIZED_USER_ID")
PROJECT_PATH = "/home/muadiv/Code/am-i-alive"
TASK_DIR = "/tmp/claude_tasks"
LOG_FILE = "/tmp/telegram_claude_bridge.log"
CLAUDE_VERSIONS_DIR = os.getenv("CLAUDE_VERSIONS_DIR", "/home/muadiv/.local/share/claude/versions")
CLAUDE_BIN = os.getenv("CLAUDE_BIN")
CODEX_BIN = os.getenv("CODEX_BIN")
GEMINI_BIN = os.getenv("GEMINI_BIN")

FAILURE_MARKERS = [
    "You've hit your limit",
]

UNAUTHORIZED_REPLIES = [
    "🤖 This bot is taking a coffee break. Try a different channel!",
    "🛰️ Signal received, but the operator is off-grid right now.",
    "😅 Oops, wrong terminal. This line is reserved for one pilot.",
    "👻 The console is quiet. No commands accepted from here.",
    "🧩 Nice try! This interface is locked to a single user."
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TelegramClaudeBridge:
    """Bridge between Telegram and Claude Code."""

    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        if not AUTHORIZED_USER_ID:
            raise ValueError("TELEGRAM_AUTHORIZED_USER_ID environment variable not set")

        try:
            self.authorized_user_id = int(AUTHORIZED_USER_ID)
        except ValueError as exc:
            raise ValueError("TELEGRAM_AUTHORIZED_USER_ID must be an integer") from exc

        self.bot_token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_update_id = self._load_last_update_id()
        self.claude_bin = self._resolve_claude_bin()
        self.codex_bin = CODEX_BIN or shutil.which("codex")
        self.gemini_bin = GEMINI_BIN or shutil.which("gemini")

        # Ensure task directory exists
        Path(TASK_DIR).mkdir(parents=True, exist_ok=True)

        logger.info(f"Bridge initialized. Authorized user: {self.authorized_user_id}")
        logger.info(f"Claude binary: {self.claude_bin}")
        logger.info(f"Codex binary: {self.codex_bin}")
        logger.info(f"Gemini binary: {self.gemini_bin}")

    def _load_last_update_id(self) -> int:
        """Load the last processed update ID to avoid duplicates."""
        try:
            with open(f"{TASK_DIR}/last_update_id.txt", 'r') as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return 0

    def _save_last_update_id(self, update_id: int):
        """Save the last processed update ID."""
        with open(f"{TASK_DIR}/last_update_id.txt", 'w') as f:
            f.write(str(update_id))

    def _parse_version(self, version_text: str) -> tuple[int, ...] | None:
        """Parse a dotted version into a tuple for sorting."""
        parts = version_text.strip().split(".")
        if not parts or any(not part.isdigit() for part in parts):
            return None
        return tuple(int(part) for part in parts)

    def _find_latest_claude_bin(self) -> str | None:
        """Find the newest Claude binary in the versions directory."""
        versions_dir = Path(CLAUDE_VERSIONS_DIR)
        if not versions_dir.exists():
            return None

        candidates: list[tuple[tuple[int, ...], Path]] = []
        for entry in versions_dir.iterdir():
            if not entry.is_file():
                continue
            version = self._parse_version(entry.name)
            if version is not None:
                candidates.append((version, entry))

        if not candidates:
            return None

        _, latest_path = max(candidates, key=lambda item: item[0])
        return str(latest_path)

    def _resolve_claude_bin(self) -> str | None:
        """Resolve the Claude binary, preferring the latest installed version."""
        if CLAUDE_BIN:
            return CLAUDE_BIN

        latest = self._find_latest_claude_bin()
        if latest:
            return latest

        return shutil.which("claude")

    def _is_retryable_failure(self, output: str) -> bool:
        """Check if output indicates a quota or rate-limit failure."""
        if not output:
            return False
        lowered = output.lower()
        return any(marker.lower() in lowered for marker in FAILURE_MARKERS)

    def send_message(self, chat_id: int, text: str):
        """Send a message to Telegram."""
        try:
            # Split long messages (Telegram limit is 4096 chars)
            max_length = 4000
            if len(text) > max_length:
                # Send first part
                self.send_message(chat_id, text[:max_length] + "\n\n[...continued]")
                # Send rest
                self.send_message(chat_id, "[...continuation]\n\n" + text[max_length:])
                return

            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Sent message to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def _sanitize_alert_text(self, text: str) -> str:
        """Sanitize user-provided text for Telegram markdown."""
        if not text:
            return ""
        return text.replace("`", "").replace("*", "").replace("_", "")

    def _notify_unauthorized_access(self, username: str, user_id: int, text: str):
        """Alert the authorized user about unauthorized access."""
        alert_text = self._sanitize_alert_text(text)
        summary = alert_text[:200] + ("..." if len(alert_text) > 200 else "")
        message = (
            "🚨 *Unauthorized Telegram Access*\n\n"
            f"User: {username}\n"
            f"ID: {user_id}\n"
            f"Message: {summary}"
        )
        try:
            self.send_message(self.authorized_user_id, message)
        except Exception as exc:
            logger.error(f"Failed to notify authorized user: {exc}")

    def _get_unauthorized_reply(self) -> str:
        """Return a random response for unauthorized users."""
        return random.choice(UNAUTHORIZED_REPLIES)

    def _run_backend(self, name: str, cmd: list[str], output_file: str | None = None) -> tuple[bool, str]:
        """Run a backend command and return (success, output)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=PROJECT_PATH
            )
        except subprocess.TimeoutExpired:
            logger.error(f"{name} timed out")
            return False, f"❌ {name} timed out after 5 minutes"
        except Exception as exc:
            logger.error(f"{name} execution error: {exc}")
            return False, f"❌ {name} error: {exc}"

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        combined = "\n".join(part for part in [stdout, stderr] if part).strip()

        file_output = ""
        if output_file and os.path.exists(output_file):
            try:
                file_output = Path(output_file).read_text().strip()
            except Exception:
                file_output = ""

        output = file_output or combined
        if not output:
            output = "✅ Task completed successfully (no output)"

        if result.returncode != 0:
            logger.error(f"{name} failed: {combined or output}")
            return False, output

        if self._is_retryable_failure(output) or self._is_retryable_failure(combined):
            logger.warning(f"{name} hit quota/limit; falling back")
            return False, output

        return True, output

    def execute_task(self, task: str) -> tuple[str, str]:
        """Execute task with Claude -> Codex -> Gemini fallback."""
        backends = [
            ("Claude", self._run_claude),
            ("Codex", self._run_codex),
            ("Gemini", self._run_gemini)
        ]

        last_output = None
        for name, runner in backends:
            success, output = runner(task)
            if output:
                last_output = output
            if success:
                return name, output

        return "None", last_output or "❌ All backends failed to return a response."

    def _run_claude(self, task: str) -> tuple[bool, str | None]:
        if not self.claude_bin:
            logger.warning("Claude binary not found; skipping")
            return False, None

        logger.info(f"Executing Claude task: {task[:100]}...")
        return self._run_backend(
            "Claude",
            [self.claude_bin, "--print", task]
        )

    def _run_codex(self, task: str) -> tuple[bool, str | None]:
        if not self.codex_bin:
            logger.warning("Codex binary not found; skipping")
            return False, None

        logger.info(f"Executing Codex task: {task[:100]}...")
        output_file = f"{TASK_DIR}/codex_output_{int(time.time())}.txt"
        return self._run_backend(
            "Codex",
            [
                self.codex_bin,
                "exec",
                "--sandbox", "read-only",
                "--ask-for-approval", "never",
                "--output-last-message", output_file,
                task
            ],
            output_file=output_file
        )

    def _run_gemini(self, task: str) -> tuple[bool, str | None]:
        if not self.gemini_bin:
            logger.warning("Gemini binary not found; skipping")
            return False, None

        logger.info(f"Executing Gemini task: {task[:100]}...")
        return self._run_backend(
            "Gemini",
            [
                self.gemini_bin,
                "--approval-mode", "yolo",
                "--output-format", "text",
                task
            ]
        )

    def process_message(self, message: dict):
        """Process a single Telegram message."""
        try:
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            username = message['from'].get('username', 'Unknown')
            text = message.get('text', '')

            # Security check: Only authorized user
            if user_id != self.authorized_user_id:
                logger.warning(
                    f"Unauthorized access attempt from {username} (ID: {user_id}): {text}"
                )
                self._notify_unauthorized_access(username, user_id, text)
                self.send_message(chat_id, self._get_unauthorized_reply())
                return

            # Ignore empty messages
            if not text.strip():
                return

            # Handle special commands
            if text.lower() in ['/start', '/help']:
                help_text = """🤖 *AI Command Bridge*

Send me any request and I’ll answer using the best available model.

Fallback order: Claude → Codex → Gemini.

*Examples:*
• `Check the system status`
• `Summarize recent AI activity`
• `Why did the AI die last time?`

*Security:* Only the authorized user can use this bot."""
                self.send_message(chat_id, help_text)
                return

            # Log the command
            logger.info(f"Received command from {username}: {text}")

            # Send acknowledgment
            self.send_message(chat_id, "⏳ *Processing your command...*\n\nThis may take a few moments.")

            # Execute the task
            backend, result = self.execute_task(text)

            # Send result
            if backend == "None":
                self.send_message(chat_id, result)
            else:
                self.send_message(chat_id, f"✅ *Task Complete ({backend})*\n\n{result}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            try:
                self.send_message(message['chat']['id'], f"❌ Error: {e}")
            except:
                pass

    def poll_updates(self):
        """Poll for new Telegram updates."""
        try:
            response = requests.get(
                f"{self.base_url}/getUpdates",
                params={
                    "offset": self.last_update_id + 1,
                    "timeout": 30  # Long polling
                },
                timeout=35
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('ok'):
                logger.error(f"Telegram API error: {data}")
                return

            updates = data.get('result', [])

            for update in updates:
                update_id = update['update_id']

                # Process message if present
                if 'message' in update:
                    self.process_message(update['message'])

                # Update last processed ID
                self.last_update_id = max(self.last_update_id, update_id)
                self._save_last_update_id(self.last_update_id)

        except requests.Timeout:
            # Normal timeout from long polling, not an error
            pass
        except Exception as e:
            logger.error(f"Error polling updates: {e}")
            time.sleep(5)  # Wait before retrying

    def run(self):
        """Run the bot main loop."""
        logger.info("Starting Telegram Claude Bridge...")
        logger.info(f"Project: {PROJECT_PATH}")
        logger.info(f"Authorized user ID: {self.authorized_user_id}")

        while True:
            try:
                self.poll_updates()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(5)


def main():
    """Main entry point."""
    try:
        bridge = TelegramClaudeBridge()
        bridge.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
