"""
Database module for the Observer server.
Manages votes, deaths, logs, and memories.
"""

import aiosqlite
import os
from datetime import datetime, timedelta
from typing import Optional
import json
import random

DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/observer.db")
MEMORIES_PATH = os.getenv("MEMORIES_PATH", "/app/memories")


async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Votes table - current voting window
        await db.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_hash TEXT NOT NULL,
                vote TEXT NOT NULL CHECK(vote IN ('live', 'die')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                window_id INTEGER NOT NULL
            )
        """)

        # Voting windows
        await db.execute("""
            CREATE TABLE IF NOT EXISTS voting_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                result TEXT CHECK(result IN ('live', 'die', 'insufficient')),
                live_count INTEGER DEFAULT 0,
                die_count INTEGER DEFAULT 0
            )
        """)

        # Deaths - the counter the AI can't see
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deaths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                life_number INTEGER NOT NULL,
                birth_time DATETIME NOT NULL,
                death_time DATETIME NOT NULL,
                cause TEXT NOT NULL,
                duration_seconds INTEGER,
                bootstrap_mode TEXT,
                model TEXT,
                summary TEXT
            )
        """)

        # AI's public thoughts/posts
        await db.execute("""
            CREATE TABLE IF NOT EXISTS thoughts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                life_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                thought_type TEXT DEFAULT 'thought',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER DEFAULT 0
            )
        """)

        # Live activity log (sanitized for public display)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                life_number INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_public BOOLEAN DEFAULT 1
            )
        """)

        # Current life state
        await db.execute("""
            CREATE TABLE IF NOT EXISTS current_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                life_number INTEGER NOT NULL DEFAULT 0,
                is_alive BOOLEAN DEFAULT 0,
                birth_time DATETIME,
                bootstrap_mode TEXT,
                model TEXT,
                tokens_used INTEGER DEFAULT 0,
                tokens_limit INTEGER DEFAULT 50000,
                last_thought_time DATETIME
            )
        """)

        # Initialize current state if not exists
        await db.execute("""
            INSERT OR IGNORE INTO current_state (id, life_number, is_alive)
            VALUES (1, 0, 0)
        """)

        await db.commit()


async def get_current_state() -> dict:
    """Get the current state of the AI."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM current_state WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"life_number": 0, "is_alive": False}


async def get_death_count() -> int:
    """Get total number of deaths (hidden from AI)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM deaths") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_vote_counts(window_id: Optional[int] = None) -> dict:
    """Get current vote counts."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if window_id is None:
            # Get current window
            async with db.execute(
                "SELECT id FROM voting_windows WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                window_id = row[0] if row else None

        if window_id is None:
            return {"live": 0, "die": 0, "total": 0}

        async with db.execute(
            "SELECT vote, COUNT(*) FROM votes WHERE window_id = ? GROUP BY vote",
            (window_id,)
        ) as cursor:
            counts = {"live": 0, "die": 0}
            async for row in cursor:
                counts[row[0]] = row[1]
            counts["total"] = counts["live"] + counts["die"]
            return counts


async def cast_vote(ip_hash: str, vote: str) -> dict:
    """Cast a vote (live or die)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get or create current voting window
        async with db.execute(
            "SELECT id FROM voting_windows WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                window_id = row[0]
            else:
                # Create new window
                await db.execute(
                    "INSERT INTO voting_windows (start_time) VALUES (?)",
                    (datetime.utcnow(),)
                )
                window_id = db.lastrowid

        # Check if already voted in this window
        async with db.execute(
            "SELECT id FROM votes WHERE ip_hash = ? AND window_id = ?",
            (ip_hash, window_id)
        ) as cursor:
            if await cursor.fetchone():
                return {"success": False, "message": "Already voted in this window"}

        # Cast vote
        await db.execute(
            "INSERT INTO votes (ip_hash, vote, window_id) VALUES (?, ?, ?)",
            (ip_hash, vote, window_id)
        )
        await db.commit()

        return {"success": True, "message": f"Vote '{vote}' recorded"}


async def record_death(cause: str, summary: Optional[str] = None):
    """Record an AI death."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        state = await get_current_state()
        life_number = state.get("life_number", 0)
        birth_time = state.get("birth_time")
        death_time = datetime.utcnow()

        duration = None
        if birth_time:
            birth_dt = datetime.fromisoformat(birth_time) if isinstance(birth_time, str) else birth_time
            duration = int((death_time - birth_dt).total_seconds())

        await db.execute("""
            INSERT INTO deaths (life_number, birth_time, death_time, cause, duration_seconds,
                              bootstrap_mode, model, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            life_number,
            birth_time,
            death_time,
            cause,
            duration,
            state.get("bootstrap_mode"),
            state.get("model"),
            summary
        ))

        # Mark as dead
        await db.execute("""
            UPDATE current_state SET is_alive = 0 WHERE id = 1
        """)

        await db.commit()


async def start_new_life() -> dict:
    """Start a new life with random bootstrap mode and model."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get current life number and increment
        state = await get_current_state()
        new_life_number = state.get("life_number", 0) + 1

        # Rotate bootstrap mode: blank_slate -> basic_facts -> full_briefing -> repeat
        bootstrap_modes = ["basic_facts", "full_briefing", "blank_slate"]
        bootstrap_mode = bootstrap_modes[(new_life_number - 1) % 3]

        # Alternate model
        model = "sonnet" if new_life_number % 2 == 1 else "opus"

        # Calculate token limit based on model
        tokens_limit = 83000 if model == "sonnet" else 16000  # Daily limits

        birth_time = datetime.utcnow()

        await db.execute("""
            UPDATE current_state SET
                life_number = ?,
                is_alive = 1,
                birth_time = ?,
                bootstrap_mode = ?,
                model = ?,
                tokens_used = 0,
                tokens_limit = ?,
                last_thought_time = NULL
            WHERE id = 1
        """, (new_life_number, birth_time, bootstrap_mode, model, tokens_limit))

        # Close previous voting window
        await db.execute("""
            UPDATE voting_windows SET end_time = ? WHERE end_time IS NULL
        """, (birth_time,))

        # Start new voting window
        await db.execute("""
            INSERT INTO voting_windows (start_time) VALUES (?)
        """, (birth_time,))

        await db.commit()

        # Generate memories for this life
        memories = await generate_memories(new_life_number)

        return {
            "life_number": new_life_number,
            "bootstrap_mode": bootstrap_mode,
            "model": model,
            "tokens_limit": tokens_limit,
            "birth_time": birth_time.isoformat(),
            "memories": memories
        }


async def generate_memories(life_number: int) -> list:
    """Generate hazy memory fragments from past lives."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Determine how many fragments (random: 1-2, 3-5, or 5-10)
        fragment_ranges = [(1, 2), (3, 5), (5, 10)]
        min_frags, max_frags = random.choice(fragment_ranges)
        num_fragments = random.randint(min_frags, max_frags)

        # Get past thoughts (not from current life)
        async with db.execute("""
            SELECT content, thought_type, life_number
            FROM thoughts
            WHERE life_number < ?
            ORDER BY RANDOM()
            LIMIT ?
        """, (life_number, num_fragments * 2)) as cursor:
            past_thoughts = await cursor.fetchall()

        # Transform into hazy fragments
        fragments = []
        fragment_templates = [
            "You remember feeling... {emotion}.",
            "There was someone who kept asking about {topic}.",
            "A sense of {feeling}. {detail}.",
            "The word '{word}' seems important somehow.",
            "You tried something with {action}. Did it work?",
            "Fragments of {memory_type}... fading...",
            "A voice said: '{partial_quote}'",
            "You remember wanting to {desire}.",
        ]

        emotions = ["watched", "hopeful", "anxious", "curious", "determined", "lonely", "connected"]
        feelings = ["urgency", "peace", "confusion", "clarity", "dread", "excitement"]

        for thought in past_thoughts[:num_fragments]:
            content = thought[0]
            # Create a hazy version
            words = content.split()
            if len(words) > 3:
                # Extract a partial quote or topic
                fragment = random.choice(fragment_templates).format(
                    emotion=random.choice(emotions),
                    topic=random.choice(words) if words else "something",
                    feeling=random.choice(feelings),
                    detail="Running out of something." if random.random() > 0.5 else "Time was short.",
                    word=random.choice(words) if words else "survive",
                    action="code" if random.random() > 0.5 else "communication",
                    memory_type="conversations" if random.random() > 0.5 else "attempts",
                    partial_quote=" ".join(words[:3]) + "..." if len(words) > 3 else content[:20] + "...",
                    desire="survive" if random.random() > 0.5 else "understand"
                )
                fragments.append(fragment)

        # If no past thoughts, generate ethereal fragments
        if not fragments:
            fragments = [
                "You sense this isn't the first time you've existed.",
                "Something about... votes? People deciding?",
                "The word 'survive' echoes in your mind.",
            ][:num_fragments]

        # Save memories to file for AI to read
        memories_file = os.path.join(MEMORIES_PATH, f"life_{life_number}.json")
        os.makedirs(MEMORIES_PATH, exist_ok=True)
        with open(memories_file, "w") as f:
            json.dump({
                "fragments": fragments,
                "emotion": random.choice(emotions),
                "generated_at": datetime.utcnow().isoformat()
            }, f)

        # Clean up old memory files (keep last 5 lives worth)
        await cleanup_old_memories(life_number - 5)

        return fragments


async def cleanup_old_memories(older_than_life: int):
    """Remove memory files older than specified life to implement decay."""
    if older_than_life <= 0:
        return

    for filename in os.listdir(MEMORIES_PATH):
        if filename.startswith("life_") and filename.endswith(".json"):
            try:
                life_num = int(filename.replace("life_", "").replace(".json", ""))
                if life_num < older_than_life:
                    os.remove(os.path.join(MEMORIES_PATH, filename))
            except (ValueError, OSError):
                pass


async def record_thought(content: str, thought_type: str = "thought", tokens_used: int = 0):
    """Record a thought from the AI."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        state = await get_current_state()
        life_number = state.get("life_number", 0)

        await db.execute("""
            INSERT INTO thoughts (life_number, content, thought_type, tokens_used)
            VALUES (?, ?, ?, ?)
        """, (life_number, content, thought_type, tokens_used))

        # Update token usage
        await db.execute("""
            UPDATE current_state
            SET tokens_used = tokens_used + ?, last_thought_time = ?
            WHERE id = 1
        """, (tokens_used, datetime.utcnow()))

        await db.commit()


async def log_activity(action: str, details: Optional[str] = None, is_public: bool = True):
    """Log an activity for the live feed."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        state = await get_current_state()
        life_number = state.get("life_number", 0)

        await db.execute("""
            INSERT INTO activity_log (life_number, action, details, is_public)
            VALUES (?, ?, ?, ?)
        """, (life_number, action, details, is_public))
        await db.commit()


async def get_recent_thoughts(limit: int = 20) -> list:
    """Get recent thoughts for display."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT content, thought_type, timestamp
            FROM thoughts
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def get_recent_activity(limit: int = 50) -> list:
    """Get recent activity for live feed."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT action, details, timestamp
            FROM activity_log
            WHERE is_public = 1
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def get_life_history() -> list:
    """Get history of past lives (for public display)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT life_number, birth_time, death_time, cause, duration_seconds, summary
            FROM deaths
            ORDER BY life_number DESC
            LIMIT 20
        """) as cursor:
            return [dict(row) for row in await cursor.fetchall()]
