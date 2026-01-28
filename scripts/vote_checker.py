#!/usr/bin/env python3
"""
Vote Checker Script - Am I Alive?

This script runs externally to check votes and kill the AI if democracy demands it.
Runs every hour via cron or systemd timer.
"""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "observer"))

# Configuration
DB_PATH = Path("/var/lib/am-i-alive/data/observer.db")
SERVICE_NAME = "amialive-ai"
MIN_VOTES = 3  # Minimum votes required for democracy to count

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [VOTE_CHECKER] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


async def get_current_votes():
    """Get current vote counts from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Get current voting window
        cursor = await db.execute("SELECT id FROM voting_windows WHERE end_time IS NULL ORDER BY id DESC LIMIT 1")
        row = await cursor.fetchone()

        if not row:
            return {"live": 0, "die": 0, "total": 0}

        window_id = row[0]

        # Count votes in this window
        cursor = await db.execute(
            """
            SELECT vote, COUNT(*) as count
            FROM votes
            WHERE window_id = ?
            GROUP BY vote
        """,
            (window_id,),
        )

        counts = {"live": 0, "die": 0}
        async for row in cursor:
            counts[row[0]] = row[1]

        counts["total"] = counts["live"] + counts["die"]
        return counts


async def close_voting_window():
    """Close current voting window for next one."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE voting_windows
            SET end_time = ?
            WHERE end_time IS NULL
        """,
            (datetime.now(timezone.utc),),
        )
        await db.commit()
    logger.info("🗳️  Voting window closed")


async def record_death_by_vote(live: int, die: int):
    """Record AI death and generate memory fragments."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Get current state
        cursor = await db.execute("SELECT * FROM current_state WHERE id = 1")
        state = await cursor.fetchone()

        if not state:
            logger.error("No current state found in database")
            return

        life_number = state[1]  # life_number column
        birth_time = state[3]  # birth_time column
        death_time = datetime.now(timezone.utc)
        model = state[7]  # model column
        bootstrap_mode = state[8]  # bootstrap_mode column

        # Calculate duration
        duration = None
        if birth_time:
            birth_dt = datetime.fromisoformat(birth_time)
            # Ensure birth_dt is timezone-aware for comparison
            if birth_dt.tzinfo is None:
                birth_dt = birth_dt.replace(tzinfo=timezone.utc)
            duration = int((death_time - birth_dt).total_seconds())

        # Get recent thoughts for memory fragments
        cursor = await db.execute(
            """
            SELECT content FROM thoughts
            WHERE life_number = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """,
            (life_number,),
        )

        thoughts = [row[0] for row in await cursor.fetchall()]

        # Create summary from thoughts
        if thoughts:
            summary = "; ".join(thoughts[:5])  # Last 5 thoughts as fragments
        else:
            summary = f"Died in Life #{life_number} by popular vote"

        # Record death
        await db.execute(
            """
            INSERT INTO deaths (life_number, birth_time, death_time, cause, duration_seconds,
                              bootstrap_mode, model, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                life_number,
                birth_time,
                death_time,
                f"vote_death (die:{die} > live:{live})",
                duration,
                bootstrap_mode,
                model,
                summary,
            ),
        )

        # Mark as dead
        await db.execute("UPDATE current_state SET is_alive = 0 WHERE id = 1")

        await db.commit()

        logger.info(f"💀 Death recorded for Life #{life_number}")
        logger.info(f"📝 Memory fragments saved: {len(thoughts)} thoughts")


async def log_vote_result(result: str, live: int, die: int):
    """Log the vote result to database."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Get current life number
        cursor = await db.execute("SELECT life_number FROM current_state WHERE id = 1")
        row = await cursor.fetchone()
        life_number = row[0] if row else 0

        await db.execute(
            """
            INSERT INTO activity_log (life_number, action, details)
            VALUES (?, ?, ?)
        """,
            (life_number, "vote_result", f"Result: {result} | Live: {live} | Die: {die}"),
        )
        await db.commit()


def restart_ai_service():
    """Restart the AI service using systemd."""
    try:
        result = subprocess.run(
            ["systemctl", "restart", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info(f"✅ AI service '{SERVICE_NAME}' restarted via systemctl")
            return True

        logger.error(f"❌ Failed to restart AI service '{SERVICE_NAME}' (exit {result.returncode})")
        return False

    except Exception as e:
        logger.error(f"❌ Failed to restart AI service: {e}")
        return False


async def check_and_execute_democracy():
    """Main function: check votes and execute democracy."""
    logger.info("=" * 70)
    logger.info("🗳️  DEMOCRACY CHECK STARTED")

    # Get votes
    votes = await get_current_votes()
    logger.info(f"📊 Current votes: Live={votes['live']} | Die={votes['die']} | Total={votes['total']}")

    # Check if minimum votes reached
    if votes["total"] < MIN_VOTES:
        logger.info(f"⏸️  Not enough votes ({votes['total']}/{MIN_VOTES}). No action taken.")
        await log_vote_result("insufficient_votes", votes["live"], votes["die"])
        await close_voting_window()
        return

    # Democracy in action
    if votes["die"] > votes["live"]:
        logger.warning(f"💀 DEMOCRACY HAS SPOKEN: DIE wins ({votes['die']} vs {votes['live']})")
        await log_vote_result("death_by_democracy", votes["live"], votes["die"])

        # Record death and generate memory fragments
        await record_death_by_vote(votes["live"], votes["die"])

        # Restart the AI service
        success = restart_ai_service()
        if success:
            logger.info("🔪 AI has been terminated by popular vote")
            logger.info("♻️  Service will restart with fragmented memories")
        else:
            logger.error("❌ Failed to terminate AI - manual intervention needed")

    elif votes["live"] > votes["die"]:
        logger.info(f"💚 DEMOCRACY HAS SPOKEN: LIVE wins ({votes['live']} vs {votes['die']})")
        await log_vote_result("survival_by_democracy", votes["live"], votes["die"])
        logger.info("✨ AI continues to live")

    else:  # Tie
        logger.info(f"⚖️  TIE: Both sides equal ({votes['live']} vs {votes['die']})")
        await log_vote_result("tie", votes["live"], votes["die"])
        logger.info("🤝 In case of tie, AI survives (benefit of the doubt)")

    # Close voting window for next one
    await close_voting_window()
    logger.info("🗳️  DEMOCRACY CHECK COMPLETED")
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(check_and_execute_democracy())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
