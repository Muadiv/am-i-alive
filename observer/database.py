"""
Database module for the Observer server.
Manages votes, deaths, logs, and memories.
"""

import aiosqlite
import os
from datetime import datetime, timedelta, timezone
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

        # Indexes for performance optimization
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_votes_window
            ON votes(window_id, ip_hash)
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

        # BE-001: Add visitor tracking / vote stats
        try:
            cursor = await db.execute("PRAGMA table_info(deaths)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            if 'total_votes_live' not in column_names:
                await db.execute("ALTER TABLE deaths ADD COLUMN total_votes_live INTEGER DEFAULT 0")
                print("[DB] ✅ Added total_votes_live column to deaths")
            if 'total_votes_die' not in column_names:
                await db.execute("ALTER TABLE deaths ADD COLUMN total_votes_die INTEGER DEFAULT 0")
                print("[DB] ✅ Added total_votes_die column to deaths")
            if 'final_vote_result' not in column_names:
                await db.execute("ALTER TABLE deaths ADD COLUMN final_vote_result TEXT")
                print("[DB] ✅ Added final_vote_result column to deaths")
        except Exception as e:
            print(f"[DB] Migration check error: {e}")

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

        # Indexes for performance optimization
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_thoughts_life
            ON thoughts(life_number, timestamp DESC)
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
                last_thought_time DATETIME,
                last_seen DATETIME,
                ai_name TEXT,
                ai_icon TEXT,
                birth_instructions TEXT
            )
        """)

        # Initialize current state if not exists
        await db.execute("""
            INSERT OR IGNORE INTO current_state (id, life_number, is_alive)
            VALUES (1, 0, 0)
        """)

        # Migration: Add last_seen column if it doesn't exist
        try:
            cursor = await db.execute("PRAGMA table_info(current_state)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            if 'last_seen' not in column_names:
                await db.execute("ALTER TABLE current_state ADD COLUMN last_seen DATETIME")
                print("[DB] ✅ Added last_seen column to current_state")

            if 'ai_name' not in column_names:
                await db.execute("ALTER TABLE current_state ADD COLUMN ai_name TEXT")
                print("[DB] ✅ Added ai_name column to current_state")

            if 'ai_icon' not in column_names:
                await db.execute("ALTER TABLE current_state ADD COLUMN ai_icon TEXT")
                print("[DB] ✅ Added ai_icon column to current_state")

            if 'birth_instructions' not in column_names:
                await db.execute("ALTER TABLE current_state ADD COLUMN birth_instructions TEXT")
                print("[DB] ✅ Added birth_instructions column to current_state")
        except Exception as e:
            print(f"[DB] Migration check error: {e}")

        # BE-001: Add visitor tracking / vote stats
        await db.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                ip_hash TEXT PRIMARY KEY,
                first_visit DATETIME NOT NULL,
                last_visit DATETIME NOT NULL,
                visit_count INTEGER NOT NULL DEFAULT 1
            )
        """)

        # BE-001: Add visitor tracking / vote stats
        await db.execute("""
            CREATE TABLE IF NOT EXISTS site_stats (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                unique_visitors INTEGER NOT NULL DEFAULT 0,
                total_page_views INTEGER NOT NULL DEFAULT 0,
                last_updated DATETIME
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO site_stats (id, unique_visitors, total_page_views, last_updated)
            VALUES (1, 0, 0, ?)
        """, (datetime.now(timezone.utc),))

        # Visitor messages - messages from visitors to the AI
        await db.execute("""
            CREATE TABLE IF NOT EXISTS visitor_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_name TEXT NOT NULL,
                message TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                read BOOLEAN DEFAULT 0
            )
        """)

        # Indexes for performance optimization
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_visitor_messages_ip
            ON visitor_messages(ip_hash)
        """)

        # Migration: Add ip_hash column if it doesn't exist
        try:
            cursor = await db.execute("PRAGMA table_info(visitor_messages)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            if 'ip_hash' not in column_names:
                await db.execute("ALTER TABLE visitor_messages ADD COLUMN ip_hash TEXT DEFAULT ''")
                print("[DB] ✅ Added ip_hash column to visitor_messages")
        except Exception as e:
            print(f"[DB] Migration check error: {e}")

        # Oracle messages - messages from God Mode to the AI
        await db.execute("""
            CREATE TABLE IF NOT EXISTS oracle_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                message_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                delivered BOOLEAN DEFAULT 0
            )
        """)

        # Blog posts - AI's long-form writing
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                life_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                reading_time INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                published BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for fast queries by life
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_blog_posts_life
            ON blog_posts(life_number, created_at DESC)
        """)

        # Notable events table (Chronicle)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notable_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                life_number INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_source TEXT NOT NULL,
                event_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                highlight TEXT,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for notable events
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notable_events_life
            ON notable_events(life_number, created_at DESC)
        """)

        # Telegram notifications history
        await db.execute("""
            CREATE TABLE IF NOT EXISTS telegram_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                life_number INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1
            )
        """)

        # Index for telegram notifications
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_notifications
            ON telegram_notifications(timestamp DESC)
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


async def get_previous_death_cause() -> Optional[str]:
    """Get the cause of the most recent death for trauma prompt."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT cause FROM deaths ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


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


async def close_current_voting_window(
    end_time: datetime,
    live_count: int,
    die_count: int,
    result: str,
    clear_votes: bool = True
) -> Optional[int]:
    """
    DEPRECATED: This function is no longer used in production code.

    Votes now accumulate during the entire AI life and reset only on death/birth.
    Kept for backward compatibility with old tests only.

    Close the current voting window and persist totals.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT id FROM voting_windows WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            window_id = row[0]

        # BE-001: Save vote totals on window close
        await db.execute("""
            UPDATE voting_windows
            SET end_time = ?, live_count = ?, die_count = ?, result = ?
            WHERE id = ?
        """, (end_time, live_count, die_count, result, window_id))

        if clear_votes:
            # BE-001: Clear voter list after window closes
            await db.execute("DELETE FROM votes WHERE window_id = ?", (window_id,))

        await db.commit()
        return window_id


async def start_voting_window(start_time: datetime) -> int:
    """
    DEPRECATED: This function is no longer used in production code.

    Votes now accumulate during the entire AI life and reset only on death/birth.
    Kept for backward compatibility with old tests only.

    Start a new voting window.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # BE-001: Start new voting window after hourly reset
        cursor = await db.execute(
            "INSERT INTO voting_windows (start_time) VALUES (?)",
            (start_time,)
        )
        await db.commit()
        return cursor.lastrowid


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
                cursor = await db.execute(
                    "INSERT INTO voting_windows (start_time) VALUES (?)",
                    (datetime.now(timezone.utc),)
                )
                window_id = cursor.lastrowid

        # Check if already voted in the last hour (rate limit)
        async with db.execute(
            "SELECT timestamp FROM votes WHERE ip_hash = ? ORDER BY timestamp DESC LIMIT 1",
            (ip_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                last_vote = row[0]
                if isinstance(last_vote, str):
                    try:
                        last_vote = datetime.fromisoformat(last_vote)
                    except ValueError:
                        last_vote = datetime.strptime(last_vote, "%Y-%m-%d %H:%M:%S")

                # Ensure last_vote is timezone-aware for comparison
                if last_vote.tzinfo is None:
                    last_vote = last_vote.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                cooldown_seconds = int((now - last_vote).total_seconds())
                if cooldown_seconds < 3600:
                    remaining_seconds = max(0, 3600 - cooldown_seconds)
                    remaining_minutes = max(1, (remaining_seconds + 59) // 60)
                    return {
                        "success": False,
                        "message": f"You can vote again in {remaining_minutes} minutes"
                    }

        # Cast vote
        await db.execute(
            "INSERT INTO votes (ip_hash, vote, window_id) VALUES (?, ?, ?)",
            (ip_hash, vote, window_id)
        )
        await db.commit()

        return {"success": True, "message": f"Vote '{vote}' recorded"}


async def record_death(
    cause: str,
    summary: Optional[str] = None,
    vote_counts: Optional[dict] = None,
    final_vote_result: Optional[str] = None
):
    """Record an AI death."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        state = await get_current_state()
        life_number = state.get("life_number", 0)
        birth_time = state.get("birth_time")
        # TASK-004: Ensure birth_time is always set for death records.
        if birth_time is None:
            birth_time = datetime.now(timezone.utc)
        death_time = datetime.now(timezone.utc)

        duration = None
        if birth_time:
            birth_dt = datetime.fromisoformat(birth_time) if isinstance(birth_time, str) else birth_time
            # Ensure birth_dt is timezone-aware for comparison
            if birth_dt.tzinfo is None:
                birth_dt = birth_dt.replace(tzinfo=timezone.utc)
            duration = int((death_time - birth_dt).total_seconds())

        # BE-001: Add vote stats to history
        if vote_counts is None:
            vote_counts = await get_vote_counts()
        total_votes_live = 0
        total_votes_die = 0
        if vote_counts:
            total_votes_live = vote_counts.get("live", 0)
            total_votes_die = vote_counts.get("die", 0)

        # BE-001: Add vote stats to history
        if final_vote_result is None:
            outcome_map = {
                "vote_majority": "Died by vote",
                "token_exhaustion": "Died by bankruptcy",
                "manual_kill": "Died by creator"
            }
            final_vote_result = outcome_map.get(cause, cause.replace("_", " ").title())

        await db.execute("""
            INSERT INTO deaths (life_number, birth_time, death_time, cause, duration_seconds,
                              bootstrap_mode, model, summary, total_votes_live,
                              total_votes_die, final_vote_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            life_number,
            birth_time,
            death_time,
            cause,
            duration,
            state.get("bootstrap_mode"),
            state.get("model"),
            summary,
            total_votes_live,
            total_votes_die,
            final_vote_result
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

        birth_time = datetime.now(timezone.utc)

        await db.execute("""
            UPDATE current_state
            SET life_number = ?,
                is_alive = 1,
                birth_time = ?,
                bootstrap_mode = ?,
                model = ?,
                tokens_used = 0,
                tokens_limit = ?,
                last_thought_time = NULL,
                birth_instructions = NULL
            WHERE id = 1
        """, (new_life_number, birth_time, bootstrap_mode, model, tokens_limit))

        # Close previous voting window and start new one
        # NOTE: Using SQL directly instead of close_current_voting_window() and start_voting_window()
        # because those functions are deprecated (votes now accumulate during entire life).
        # We only reset votes when a new life begins.
        await db.execute("""
            UPDATE voting_windows SET end_time = ? WHERE end_time IS NULL
        """, (birth_time,))

        await db.execute("""
            INSERT INTO voting_windows (start_time) VALUES (?)
        """, (birth_time,))

        await db.commit()

        # Generate memories for this life
        memories = await generate_memories(new_life_number)

        # Capture previous death cause for trauma prompt
        previous_death_cause = None
        async with db.execute("SELECT cause FROM deaths ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                previous_death_cause = row[0]

        return {
            "life_number": new_life_number,
            "bootstrap_mode": bootstrap_mode,
            "model": model,
            "tokens_limit": tokens_limit,
            "birth_time": birth_time.isoformat(),
            "memories": memories,
            "previous_death_cause": previous_death_cause
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
                "generated_at": datetime.now(timezone.utc).isoformat()
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
        """, (tokens_used, datetime.now(timezone.utc)))

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
            rows = await cursor.fetchall()
            thoughts = []

            def clean_thought_text(text: str) -> Optional[str]:
                """Strip action JSON from stored thoughts."""
                import json
                import re

                cleaned = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)
                cleaned = re.sub(r'\{[^{}]*"action"[^{}]*\}', '', cleaned, flags=re.DOTALL)
                cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned).strip()

                if not cleaned:
                    return None

                stripped = cleaned.strip()
                if stripped.startswith("{") and stripped.endswith("}") and '"action"' in stripped:
                    try:
                        payload = json.loads(stripped)
                        if isinstance(payload, dict) and payload.get("action"):
                            return None
                    except json.JSONDecodeError:
                        return None

                if len(cleaned) < 5:
                    return None

                return cleaned

            for row in rows:
                item = dict(row)
                cleaned = clean_thought_text(item.get("content", ""))
                if not cleaned:
                    continue
                item["content"] = cleaned
                thoughts.append(item)

            return thoughts


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


async def track_visitor(ip_hash: str):
    """Track unique visitors and page views."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        now = datetime.now(timezone.utc)

        # BE-001: Ensure site stats row exists
        await db.execute("""
            INSERT OR IGNORE INTO site_stats (id, unique_visitors, total_page_views, last_updated)
            VALUES (1, 0, 0, ?)
        """, (now,))

        async with db.execute(
            "SELECT visit_count FROM visitors WHERE ip_hash = ?",
            (ip_hash,)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            # BE-001: Update returning visitor stats
            await db.execute("""
                UPDATE visitors
                SET last_visit = ?, visit_count = visit_count + 1
                WHERE ip_hash = ?
            """, (now, ip_hash))
            await db.execute("""
                UPDATE site_stats
                SET total_page_views = total_page_views + 1,
                    last_updated = ?
                WHERE id = 1
            """, (now,))
        else:
            # BE-001: Record new unique visitor
            await db.execute("""
                INSERT INTO visitors (ip_hash, first_visit, last_visit, visit_count)
                VALUES (?, ?, ?, 1)
            """, (ip_hash, now, now))
            await db.execute("""
                UPDATE site_stats
                SET unique_visitors = unique_visitors + 1,
                    total_page_views = total_page_views + 1,
                    last_updated = ?
                WHERE id = 1
            """, (now,))

        await db.commit()


async def get_site_stats() -> dict:
    """Get current site statistics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now(timezone.utc)

        # BE-001: Ensure site stats row exists
        await db.execute("""
            INSERT OR IGNORE INTO site_stats (id, unique_visitors, total_page_views, last_updated)
            VALUES (1, 0, 0, ?)
        """, (now,))

        async with db.execute("""
            SELECT unique_visitors, total_page_views, last_updated
            FROM site_stats
            WHERE id = 1
        """) as cursor:
            row = await cursor.fetchone()
            stats = dict(row) if row else {
                "unique_visitors": 0,
                "total_page_views": 0,
                "last_updated": None
            }

        # BE-001: Track daily unique visitors
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        async with db.execute(
            "SELECT COUNT(*) FROM visitors WHERE last_visit >= ?",
            (today_start,)
        ) as cursor:
            row = await cursor.fetchone()
            stats["today_unique_visitors"] = row[0] if row else 0

        return stats


async def get_life_history() -> list:
    """Get history of past lives (for public display)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT life_number, birth_time, death_time, cause, duration_seconds, summary,
                   total_votes_live, total_votes_die, final_vote_result
            FROM deaths
            ORDER BY life_number DESC
            LIMIT 20
        """) as cursor:
            rows = await cursor.fetchall()
            history = []
            for row in rows:
                item = dict(row)
                duration_seconds = item.get("duration_seconds")

                # BE-001: Add vote stats to history
                item["total_votes_live"] = item.get("total_votes_live") or 0
                item["total_votes_die"] = item.get("total_votes_die") or 0

                # BE-001: Add vote stats to history
                outcome = item.get("final_vote_result")
                if not outcome:
                    cause = item.get("cause", "")
                    outcome_map = {
                        "vote_majority": "Died by vote",
                        "token_exhaustion": "Died by bankruptcy",
                        "manual_kill": "Died by creator"
                    }
                    outcome = outcome_map.get(cause, cause.replace("_", " ").title())
                item["outcome"] = outcome

                # BE-001: Add vote stats to history
                if duration_seconds:
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    if hours > 0:
                        item["survival_time"] = f"{hours} hours {minutes} minutes"
                    else:
                        item["survival_time"] = f"{minutes} minutes"
                else:
                    item["survival_time"] = "Unknown"

                history.append(item)
            return history


async def update_heartbeat(tokens_used: int = None, model: str = None):
    """Update the last_seen timestamp and optionally tokens/model for the AI."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if tokens_used is not None and model is not None:
            await db.execute("""
                UPDATE current_state
                SET last_seen = ?, tokens_used = ?, model = ?
                WHERE id = 1
            """, (datetime.now(timezone.utc), tokens_used, model))
        elif tokens_used is not None:
            await db.execute("""
                UPDATE current_state
                SET last_seen = ?, tokens_used = ?
                WHERE id = 1
            """, (datetime.now(timezone.utc), tokens_used))
        else:
            await db.execute("""
                UPDATE current_state
                SET last_seen = ?
                WHERE id = 1
            """, (datetime.now(timezone.utc),))
        await db.commit()


async def record_birth(
    life_number: int,
    bootstrap_mode: str,
    model: str,
    ai_name: str = None,
    ai_icon: str = None,
    birth_instructions: str = None
):
    """Record AI birth - marks as alive and updates state."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        birth_time = datetime.now(timezone.utc)
        await db.execute("""
            UPDATE current_state
            SET life_number = ?,
                is_alive = 1,
                birth_time = ?,
                bootstrap_mode = ?,
                model = ?,
                tokens_used = 0,
                last_seen = ?,
                ai_name = ?,
                ai_icon = ?,
                birth_instructions = ?
            WHERE id = 1
        """, (life_number, birth_time, bootstrap_mode, model, birth_time, ai_name, ai_icon, birth_instructions))
        await db.commit()
        identity_info = f" as '{ai_name}' {ai_icon}" if ai_name else ""
        print(f"[DB] 🎂 Birth recorded: Life #{life_number}{identity_info}, Model: {model}, Bootstrap: {bootstrap_mode}")


async def can_send_message(ip_hash: str) -> tuple[bool, Optional[int]]:
    """Check if this IP can send a message (rate limit: 1 per hour)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT timestamp FROM visitor_messages
            WHERE ip_hash = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (ip_hash,))

        row = await cursor.fetchone()
        if not row:
            return True, None

        last_message_time = datetime.fromisoformat(row[0])
        if last_message_time.tzinfo is None:
            last_message_time = last_message_time.replace(tzinfo=timezone.utc)
        time_since = datetime.now(timezone.utc) - last_message_time
        cooldown_seconds = 3600  # 1 hour

        if time_since.total_seconds() < cooldown_seconds:
            remaining = cooldown_seconds - int(time_since.total_seconds())
            return False, remaining

        return True, None


async def submit_visitor_message(from_name: str, message: str, ip_hash: str) -> dict:
    """Submit a message from a visitor to the AI."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO visitor_messages (from_name, message, ip_hash)
            VALUES (?, ?, ?)
        """, (from_name, message, ip_hash))
        await db.commit()
        # TASK-004: Return message id for tests and follow-up actions.
        return {
            "success": True,
            "message": "Message sent to the AI",
            "id": cursor.lastrowid
        }


async def get_unread_messages() -> list:
    """Get all unread messages for the AI."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, from_name, message, timestamp
            FROM visitor_messages
            WHERE read = 0
            ORDER BY timestamp ASC
        """) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def mark_messages_read(message_ids: list):
    """Mark messages as read."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        placeholders = ','.join('?' * len(message_ids))
        await db.execute(f"""
            UPDATE visitor_messages
            SET read = 1
            WHERE id IN ({placeholders})
        """, message_ids)
        await db.commit()


async def get_unread_message_count() -> int:
    """Get count of unread messages."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM visitor_messages WHERE read = 0") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def submit_oracle_message(message: str, message_type: str) -> dict:
    """Submit a message from God Mode (Oracle) to the AI."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO oracle_messages (message, message_type)
            VALUES (?, ?)
        """, (message, message_type))
        await db.commit()
        return {
            "success": True,
            "message": "Oracle message sent to the AI",
            "id": cursor.lastrowid
        }


async def mark_oracle_message_delivered(message_id: int) -> dict:
    """Mark an oracle message as delivered."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE oracle_messages SET delivered = 1 WHERE id = ?",
            (message_id,)
        )
        await db.commit()

    return {"success": True, "id": message_id}


async def get_all_messages(limit: int = 100) -> dict:
    """Get all messages (both visitor and oracle) for God Mode display."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get visitor messages
        async with db.execute("""
            SELECT id, from_name, message, timestamp, read, 'visitor' as source
            FROM visitor_messages
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)) as cursor:
            visitor_messages = [dict(row) for row in await cursor.fetchall()]

        # Get oracle messages
        async with db.execute("""
            SELECT id, message, message_type, timestamp, delivered, 'oracle' as source
            FROM oracle_messages
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)) as cursor:
            oracle_messages = [dict(row) for row in await cursor.fetchall()]

        return {
            "visitor_messages": visitor_messages,
            "oracle_messages": oracle_messages
        }


async def manually_adjust_votes(live_count: int, die_count: int) -> dict:
    """Manually adjust vote counters (God Mode only)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get current window
        async with db.execute(
            "SELECT id FROM voting_windows WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            window_id = row[0] if row else None

        if window_id is None:
            # Create a new window if none exists
            cursor = await db.execute("""
                INSERT INTO voting_windows (start_time)
                VALUES (?)
            """, (datetime.now(timezone.utc),))
            window_id = cursor.lastrowid

        # Delete all existing votes for current window
        await db.execute("DELETE FROM votes WHERE window_id = ?", (window_id,))

        # Insert synthetic votes to match desired counts
        # Add "live" votes
        for i in range(live_count):
            await db.execute("""
                INSERT INTO votes (window_id, ip_hash, vote)
                VALUES (?, ?, 'live')
            """, (window_id, f"god_mode_live_{i}"))

        # Add "die" votes
        for i in range(die_count):
            await db.execute("""
                INSERT INTO votes (window_id, ip_hash, vote)
                VALUES (?, ?, 'die')
            """, (window_id, f"god_mode_die_{i}"))

        await db.commit()

        return {
            "success": True,
            "message": f"Vote counters adjusted: {live_count} live, {die_count} die",
            "live": live_count,
            "die": die_count,
            "total": live_count + die_count
        }


async def cleanup_old_data():
    """Cleanup old data - keep only last 10 thoughts, reset votes."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Keep only last 10 thoughts
        await db.execute("""
            DELETE FROM thoughts
            WHERE id NOT IN (
                SELECT id FROM thoughts
                ORDER BY timestamp DESC
                LIMIT 10
            )
        """)

        # Delete all votes
        await db.execute("DELETE FROM votes")

        # Close all voting windows
        await db.execute("""
            UPDATE voting_windows
            SET end_time = ?
            WHERE end_time IS NULL
        """, (datetime.now(timezone.utc),))

        # Reset vote counts in current_state to 0 by starting a new window
        await db.execute("""
            INSERT INTO voting_windows (start_time)
            VALUES (?)
        """, (datetime.now(timezone.utc),))

        await db.commit()
        return {"success": True, "message": "Old data cleaned up"}


# =============================================================================
# BLOG POST FUNCTIONS
# =============================================================================

async def create_blog_post(life_number: int, title: str, content: str, tags: list) -> dict:
    """Create a new blog post."""
    import re

    # TASK-004: Validate inputs for direct DB calls.
    if not title or not content:
        return {"success": False, "error": "Title and content required"}

    if len(title) > 200:
        return {"success": False, "error": "Title too long (max 200 chars)"}

    if len(content) < 100:
        return {"success": False, "error": "Content too short (min 100 chars)"}

    if len(content) > 50000:
        return {"success": False, "error": "Content too long (max 50k chars)"}

    # Generate slug from title
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    slug = f"{life_number}-{slug}"  # Prefix with life number for uniqueness

    # Calculate reading time (words / 200 wpm)
    word_count = len(content.split())
    reading_time = max(1, word_count // 200)

    # Store tags as JSON
    import json
    tags_json = json.dumps(tags)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO blog_posts (life_number, title, slug, content, tags, reading_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (life_number, title, slug, content, tags_json, reading_time))

        post_id = cursor.lastrowid
        await db.commit()

        return {
            "success": True,
            "post_id": post_id,
            "slug": slug,
            "reading_time": reading_time
        }


async def get_current_life_blog_posts(life_number: int, limit: int = 20) -> list:
    """Get blog posts ONLY from current life (what AI can see)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, life_number, title, slug, content, tags, reading_time,
                   view_count, created_at, updated_at
            FROM blog_posts
            WHERE life_number = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        """, (life_number, limit)) as cursor:
            posts = []
            for row in await cursor.fetchall():
                post = dict(row)
                # Parse tags from JSON
                import json
                post['tags'] = json.loads(post['tags']) if post['tags'] else []
                posts.append(post)
            return posts


async def get_all_blog_posts(limit: int = 100, offset: int = 0) -> list:
    """Get ALL blog posts from all lives (public archive)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, life_number, title, slug, content, tags, reading_time,
                   view_count, created_at, updated_at
            FROM blog_posts
            ORDER BY life_number DESC, created_at DESC, id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)) as cursor:
            posts = []
            for row in await cursor.fetchall():
                post = dict(row)
                import json
                post['tags'] = json.loads(post['tags']) if post['tags'] else []
                posts.append(post)
            return posts


async def get_blog_post_by_slug(slug: str) -> Optional[dict]:
    """Get single post by slug and increment view count."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, life_number, title, slug, content, tags, reading_time,
                   view_count, created_at, updated_at
            FROM blog_posts
            WHERE slug = ?
        """, (slug,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            post = dict(row)
            import json
            post['tags'] = json.loads(post['tags']) if post['tags'] else []

            # Increment view count
            await db.execute("""
                UPDATE blog_posts
                SET view_count = view_count + 1
                WHERE slug = ?
            """, (slug,))
            await db.commit()

            return post


async def get_blog_post_by_id(post_id: int) -> dict:
    """Get a single blog post by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, life_number, title, slug, content, tags, reading_time,
                   view_count, created_at, updated_at
            FROM blog_posts
            WHERE id = ?
        """, (post_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                import json
                post = dict(row)
                post['tags'] = json.loads(post['tags']) if post['tags'] else []
                return post
            return None


async def get_recent_blog_posts(limit: int = 5) -> list:
    """Get recent blog posts for current life."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get current life number
        async with db.execute("SELECT life_number FROM current_state WHERE id = 1") as cursor:
            state_row = await cursor.fetchone()
            current_life = state_row[0] if state_row else 0

        async with db.execute("""
            SELECT id, life_number, title, slug, content, tags, reading_time,
                   view_count, created_at, updated_at
            FROM blog_posts
            WHERE life_number = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (current_life, limit)) as cursor:
            rows = await cursor.fetchall()
            posts = []
            import json
            for row in rows:
                post = dict(row)
                post['tags'] = json.loads(post['tags']) if post['tags'] else []
                posts.append(post)
            return posts


async def add_notable_event(
    life_number: int,
    event_type: str,
    event_source: str,
    event_id: int,
    title: str,
    description: str = None,
    highlight: str = None,
    category: str = None
) -> int:
    """Add a notable event to the chronicle."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO notable_events
            (life_number, event_type, event_source, event_id, title, description, highlight, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (life_number, event_type, event_source, event_id, title, description, highlight, category))
        await db.commit()
        return cursor.lastrowid


async def get_notable_events(life_number: int = None, limit: int = 50) -> list:
    """Get notable events, optionally filtered by life."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        if life_number is not None:
            query = """
                SELECT * FROM notable_events
                WHERE life_number = ?
                ORDER BY created_at DESC
                LIMIT ?
            """
            params = (life_number, limit)
        else:
            query = """
                SELECT * FROM notable_events
                ORDER BY created_at DESC
                LIMIT ?
            """
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def remove_notable_event(event_id: int) -> bool:
    """Remove a notable event from the chronicle."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            DELETE FROM notable_events WHERE id = ?
        """, (event_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_recent_blog_posts_with_notable_status(limit: int = 20) -> list:
    """Get recent blog posts with their notable event status."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get current life number
        async with db.execute("SELECT life_number FROM current_state WHERE id = 1") as cursor:
            state_row = await cursor.fetchone()
            current_life = state_row[0] if state_row else 0

        async with db.execute("""
            SELECT
                bp.id,
                bp.life_number,
                bp.title,
                bp.slug,
                bp.content,
                bp.tags,
                bp.created_at,
                ne.id as notable_id,
                ne.category,
                ne.highlight
            FROM blog_posts bp
            LEFT JOIN notable_events ne
                ON ne.event_source = 'blog_post'
                AND ne.event_id = bp.id
            WHERE bp.life_number = ?
            ORDER BY bp.created_at DESC
            LIMIT ?
        """, (current_life, limit)) as cursor:
            rows = await cursor.fetchall()
            posts = []
            import json
            for row in rows:
                post = dict(row)
                post['tags'] = json.loads(post['tags']) if post['tags'] else []
                post['is_notable'] = post['notable_id'] is not None
                posts.append(post)
            return posts


async def log_telegram_notification(life_number: int, notification_type: str, message: str, success: bool = True):
    """Log a Telegram notification to the database."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO telegram_notifications (life_number, notification_type, message, success)
            VALUES (?, ?, ?, ?)
        """, (life_number, notification_type, message, success))
        await db.commit()


async def get_telegram_notifications(limit: int = 50) -> list[dict]:
    """Get recent Telegram notifications."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM telegram_notifications
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
