from __future__ import annotations

import asyncio
import signal
from datetime import datetime, timezone
from typing import Any, Optional

from .brain_core import AIBrain
from .brain_shared import AI_COMMAND_PORT
from .logging_config import logger
from .telegram_notifier import notifier

brain: AIBrain | None = None
is_running = True
birth_event: Optional[asyncio.Event] = None
pending_birth_data: Optional[dict[str, Any]] = None
brain_loop: Optional[asyncio.AbstractEventLoop] = None


async def heartbeat_loop() -> None:
    global brain, is_running
    logger.info("[BRAIN] 💓 Starting heartbeat loop...")
    while is_running and (not brain or brain.is_running):
        try:
            if brain and brain.is_alive:
                await brain.send_heartbeat()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Heartbeat error: {e}")
            await asyncio.sleep(30)
    logger.info("[BRAIN] 💔 Heartbeat stopped.")


async def notification_monitor() -> None:
    global brain, is_running
    logger.info("[TELEGRAM] 📡 Starting notification monitor...")

    while is_running and (not brain or brain.is_running):
        try:
            if not brain or not brain.is_alive:
                await asyncio.sleep(300)
                continue

            try:
                votes = await brain.check_votes()
                if isinstance(votes, dict):
                    identity_name = brain.identity.get("name", "Unknown") if brain.identity else "Unknown"
                    await notifier.notify_vote_status(brain.life_number or 0, identity_name, votes)
            except Exception as e:
                logger.error(f"[TELEGRAM] ⚠️ Failed to check votes: {e}")

            try:
                credit_status = brain.credit_tracker.get_status()
                remaining = credit_status.get("balance", 0.0)
                budget = credit_status.get("budget", 0.0)
                remaining_percent = (remaining / budget * 100) if budget else 0.0
                if remaining_percent < 25:
                    identity_name = brain.identity.get("name", "Unknown") if brain.identity else "Unknown"
                    await notifier.notify_budget_warning(
                        brain.life_number or 0,
                        identity_name,
                        remaining,
                        remaining_percent,
                    )
            except Exception as e:
                logger.error(f"[TELEGRAM] ⚠️ Failed to check budget: {e}")

            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"[TELEGRAM] ❌ Monitor error: {e}")
            await asyncio.sleep(300)

    logger.info("[TELEGRAM] 📴 Notification monitor stopped.")


async def moltbook_loop() -> None:
    global brain, is_running
    logger.info("[MOLTBOOK] 🦞 Starting Moltbook loop...")
    while is_running and (not brain or brain.is_running):
        try:
            if brain and brain.is_alive:
                await brain.moltbook_heartbeat()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"[MOLTBOOK] ❌ Loop error: {e}")
            await asyncio.sleep(60)
    logger.info("[MOLTBOOK] 🛑 Moltbook loop stopped.")


async def queue_birth_data(life_data: dict[str, Any]) -> None:
    global pending_birth_data
    pending_birth_data = life_data
    logger.info("[BRAIN] 📥 Birth data queued")
    if birth_event:
        birth_event.set()


async def main_loop() -> None:
    global brain, is_running, brain_loop, birth_event, pending_birth_data

    brain_loop = asyncio.get_running_loop()
    birth_event = asyncio.Event()
    brain = AIBrain()

    from .api.command_server import start_command_server

    await start_command_server(AI_COMMAND_PORT, brain, birth_event)

    logger.info("[BRAIN] ⏳ Waiting for birth data from Observer...")

    while is_running and (not brain or brain.is_running):
        if not pending_birth_data:
            await birth_event.wait()
            birth_event.clear()
        life_data = pending_birth_data
        pending_birth_data = None

        if not life_data:
            continue

        try:
            await brain.initialize(life_data)
        except Exception as e:
            logger.error(f"[BRAIN] ❌ Birth initialization failed: {e}")
            continue

        if not brain.identity:
            logger.error("[BRAIN] ❌ Identity missing after initialization")
            continue

        logger.info(f"[BRAIN] 🧠 Starting consciousness loop for {brain.identity['name']}...")

        asyncio.create_task(heartbeat_loop())
        asyncio.create_task(notification_monitor())
        asyncio.create_task(moltbook_loop())

        try:
            while is_running and brain.is_running:
                if pending_birth_data:
                    logger.info("[BRAIN] 🔁 New birth data received; restarting consciousness loop.")
                    break

                try:
                    thought = await brain.think()

                    if thought:
                        thought_preview = thought[:200] + "..." if len(thought) > 200 else thought
                        logger.info(f"[{brain.identity['name']}] 💭 {thought_preview}")

                    await asyncio.sleep(brain.current_think_interval)
                except Exception as e:
                    logger.exception(f"[BRAIN] ❌ Loop error: {e}")
                    await asyncio.sleep(60)
        finally:
            await brain.shutdown()

        logger.info(f"[BRAIN] ☠️  {brain.identity['name']}'s consciousness ended.")


def signal_handler(sig: int, frame: Any) -> None:
    global is_running
    logger.warning(f"[BRAIN] 🛑 Shutdown signal ({sig}) received...")
    is_running = False
    if brain:
        brain.is_alive = False
    if brain_loop and birth_event:
        brain_loop.call_soon_threadsafe(birth_event.set)


def run_main() -> None:
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    from .budget_server import start_budget_server

    start_budget_server(port=8001)
    logger.info("=" * 80)
    logger.info("🧠 AM I ALIVE? - Genesis Brain (OpenRouter Edition)")
    logger.info("=" * 80)
    asyncio.run(main_loop())
