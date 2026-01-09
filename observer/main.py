"""
Am I Alive? - Observer Server
The public face of the experiment: voting, viewing, and life/death control.
"""

import asyncio
import hashlib
import ipaddress
import os
import random
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse
import aiosqlite
import httpx
import markdown2

import database as db

app = FastAPI(title="Am I Alive?", description="An experiment in digital consciousness")

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# AI container API
AI_API_URL = os.getenv("AI_API_URL", "http://ai:8001")

# Voting window duration (1 hour)
VOTING_WINDOW_SECONDS = 3600

# Minimum votes required for death by voting
MIN_VOTES_FOR_DEATH = 3

# Respawn delay range (seconds)
# BE-002: Reduce respawn delay for testing
RESPAWN_DELAY_MIN = 10
RESPAWN_DELAY_MAX = 60
# BE-003: State sync validator interval (seconds)
STATE_SYNC_INTERVAL_SECONDS = 30

# Local network for God mode access
LOCAL_NETWORK = ipaddress.ip_network("192.168.0.0/24")


def is_local_request(request: Request) -> bool:
    """Check if request comes from local network."""
    if not request.client:
        return False

    try:
        client_ip = ipaddress.ip_address(request.client.host)
        return client_ip in LOCAL_NETWORK
    except ValueError:
        # Invalid IP format
        return False


def require_local_network(request: Request):
    """Raise HTTPException if request is not from local network."""
    if not is_local_request(request):
        raise HTTPException(
            status_code=403,
            detail="Access denied: God mode only accessible from local network"
        )


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await db.init_db()
    # Start background tasks
    asyncio.create_task(voting_window_checker())
    asyncio.create_task(token_budget_checker())
    asyncio.create_task(state_sync_validator())  # BE-003


# =============================================================================
# PUBLIC PAGES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page - see the AI, vote, watch it live."""
    # BE-001: Track visitors
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
    await db.track_visitor(ip_hash)

    state = await db.get_current_state()
    votes = await db.get_vote_counts()
    thoughts = await db.get_recent_thoughts(10)
    death_count = await db.get_death_count()
    message_count = await db.get_unread_message_count()
    site_stats = await db.get_site_stats()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "state": state,
        "votes": votes,
        "thoughts": thoughts,
        "death_count": death_count,
        "message_count": message_count,
        "site_stats": site_stats,
        "is_alive": state.get("is_alive", False)
    })


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    """View past lives."""
    lives = await db.get_life_history()
    death_count = await db.get_death_count()

    return templates.TemplateResponse("history.html", {
        "request": request,
        "lives": lives,
        "death_count": death_count
    })


@app.get("/budget", response_class=HTMLResponse)
async def budget_page(request: Request):
    """View AI's budget and spending."""
    # Get budget data from AI
    budget_data = {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AI_API_URL}/budget", timeout=5.0)
            budget_data = response.json()
            # BE-002: Ensure token breakdown fields exist for budget display
            budget_data.setdefault("models", [])
            budget_data.setdefault("totals", {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            })
    except Exception:
        budget_data = {"error": "Could not fetch budget data"}

    return templates.TemplateResponse("budget.html", {
        "request": request,
        "budget": budget_data
    })


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page explaining the experiment."""
    return templates.TemplateResponse("about.html", {
        "request": request
    })


@app.get("/blog", response_class=HTMLResponse)
async def blog_page(request: Request):
    """Blog homepage - current life's posts only."""
    state = await db.get_current_state()
    posts = await db.get_current_life_blog_posts(state['life_number'], limit=20)

    # Add memory fragments at the top if life > 1
    memories = []
    if state['life_number'] > 1:
        # Load memory fragments from previous life
        try:
            memory_data = await db.get_life_history()
            if memory_data:
                # Get most recent dead life
                previous_life = [l for l in memory_data if l['life_number'] == state['life_number'] - 1]
                if previous_life and previous_life[0].get('summary'):
                    # Parse summary into fragments
                    summary = previous_life[0]['summary']
                    memories = [s.strip() for s in summary.split(';') if s.strip()]
        except Exception:
            memories = []

    return templates.TemplateResponse("blog.html", {
        "request": request,
        "posts": posts,
        "state": state,
        "memories": memories,
        "is_current_life": True
    })


@app.get("/blog/history", response_class=HTMLResponse)
async def blog_history(request: Request):
    """Archive of ALL blog posts from all lives."""
    all_posts = await db.get_all_blog_posts(limit=100)

    # Group by life_number
    posts_by_life = {}
    for post in all_posts:
        life = post['life_number']
        if life not in posts_by_life:
            posts_by_life[life] = []
        posts_by_life[life].append(post)

    return templates.TemplateResponse("blog_history.html", {
        "request": request,
        "posts_by_life": posts_by_life,
        "total_posts": len(all_posts)
    })


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    """Individual blog post page."""
    post = await db.get_blog_post_by_slug(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Convert markdown to HTML
    post['html_content'] = markdown2.markdown(
        post['content'],
        extras=['fenced-code-blocks', 'tables', 'header-ids']
    )

    return templates.TemplateResponse("blog_post.html", {
        "request": request,
        "post": post
    })


@app.get("/god", response_class=HTMLResponse)
async def god_mode(request: Request):
    """God Mode interface - secret admin page (local network only)."""
    require_local_network(request)
    return templates.TemplateResponse("god.html", {
        "request": request
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/system/stats")
async def get_system_stats():
    """Return current system statistics."""
    # TASK: System stats endpoint for AI embodiment.
    import subprocess
    import psutil

    cpu_temp = "unknown"
    try:
        temp = subprocess.check_output(["vcgencmd", "measure_temp"], timeout=2).decode()
        cpu_temp = temp.replace("temp=", "").replace("'C", "").strip()
    except Exception:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp_file:
                cpu_temp = f"{float(temp_file.read().strip()) / 1000.0:.1f}"
        except Exception:
            cpu_temp = "unknown"

    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    try:
        disk = psutil.disk_usage("/app")
    except Exception:
        disk = psutil.disk_usage("/")

    state = await db.get_current_state()
    birth_time = state.get("birth_time")
    uptime_seconds = 0
    if birth_time:
        try:
            birth_dt = datetime.fromisoformat(birth_time) if isinstance(birth_time, str) else birth_time
            uptime_seconds = max(0, int((datetime.utcnow() - birth_dt).total_seconds()))
        except Exception:
            uptime_seconds = 0

    return {
        "cpu_temp": cpu_temp,
        "cpu_usage": cpu_percent,
        "ram_usage": memory.percent,
        "ram_available": f"{memory.available // (1024 * 1024)}MB",
        "disk_usage": disk.percent,
        "uptime_seconds": uptime_seconds,
        "life_number": state.get("life_number")
    }


# =============================================================================
# VOTING API
# =============================================================================

@app.post("/api/vote/{vote_type}")
async def vote(vote_type: str, request: Request):
    """Cast a vote (live or die)."""
    if vote_type not in ("live", "die"):
        raise HTTPException(status_code=400, detail="Vote must be 'live' or 'die'")

    # Check if AI is alive
    state = await db.get_current_state()
    if not state.get("is_alive"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Cannot vote - AI is currently dead"}
        )

    # Hash IP for privacy
    client_ip = request.client.host
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]

    result = await db.cast_vote(ip_hash, vote_type)

    # Log the vote (sanitized)
    await db.log_activity("vote_received", f"A visitor voted to {vote_type}")

    return result


@app.get("/api/votes")
async def get_votes():
    """Get current vote counts."""
    return await db.get_vote_counts()


@app.get("/api/next-vote-check")
async def get_next_vote_check():
    """Get time until next vote check (hourly at minute 0)."""
    from datetime import datetime, timedelta
    # BE-001: Align vote check timer with server UTC
    now = datetime.utcnow()

    # Next hour at minute 0
    next_check = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    seconds_until = int((next_check - now).total_seconds())

    return {
        "next_check": next_check.isoformat(),
        "seconds_until": seconds_until
    }


# =============================================================================
# STATE API
# =============================================================================

@app.get("/api/state")
async def get_state():
    """Get current AI state (for the AI and public)."""
    state = await db.get_current_state()
    votes = await db.get_vote_counts()

    # Remove death count - AI shouldn't know
    return {
        "is_alive": state.get("is_alive", False),
        "life_number": state.get("life_number", 0) if state.get("is_alive") else None,
        "birth_time": state.get("birth_time"),
        "tokens_used": state.get("tokens_used", 0),
        "tokens_limit": state.get("tokens_limit", 50000),
        "tokens_remaining": state.get("tokens_limit", 50000) - state.get("tokens_used", 0),
        "votes": votes,
        "bootstrap_mode": state.get("bootstrap_mode"),
        "model": state.get("model")
    }


@app.get("/api/state/full")
async def get_full_state():
    """Get full state including death count (for observers only, not AI)."""
    state = await db.get_current_state()
    votes = await db.get_vote_counts()
    death_count = await db.get_death_count()

    return {
        **state,
        "votes": votes,
        "death_count": death_count
    }


@app.get("/api/thoughts")
async def get_thoughts(limit: int = 20):
    """Get recent thoughts."""
    return await db.get_recent_thoughts(limit)


@app.get("/api/activity")
async def get_activity(limit: int = 50):
    """Get recent activity log."""
    return await db.get_recent_activity(limit)


# =============================================================================
# AI COMMUNICATION API (called by AI container)
# =============================================================================

@app.post("/api/thought")
async def receive_thought(request: Request):
    """Receive a thought from the AI."""
    data = await request.json()
    content = data.get("content", "")
    thought_type = data.get("type", "thought")
    tokens_used = data.get("tokens_used", 0)

    if not content:
        raise HTTPException(status_code=400, detail="Content required")

    await db.record_thought(content, thought_type, tokens_used)
    await db.log_activity("thought", f"AI shared a {thought_type}")

    return {"success": True}


@app.post("/api/activity")
async def receive_activity(request: Request):
    """Log an activity from the AI."""
    data = await request.json()
    action = data.get("action", "")
    details = data.get("details")

    if not action:
        raise HTTPException(status_code=400, detail="Action required")

    # Sanitize details (remove potential secrets)
    if details:
        details = sanitize_log(details)

    await db.log_activity(action, details)
    return {"success": True}


@app.post("/api/heartbeat")
async def receive_heartbeat(request: Request):
    """Receive heartbeat from the AI to mark it as alive."""
    data = {}
    try:
        data = await request.json()
    except:
        pass

    tokens_used = data.get("tokens_used", 0)
    model = data.get("model")

    await db.update_heartbeat(tokens_used=tokens_used, model=model)
    return {"success": True, "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/blog/post")
async def create_blog_post_api(request: Request):
    """AI creates a blog post."""
    data = await request.json()
    title = data.get("title", "")
    content = data.get("content", "")
    tags = data.get("tags", [])

    # Validation
    if not title or not content:
        raise HTTPException(status_code=400, detail="Title and content required")

    if len(title) > 200:
        raise HTTPException(status_code=400, detail="Title too long (max 200 chars)")

    if len(content) > 50000:
        raise HTTPException(status_code=400, detail="Content too long (max 50k chars)")

    # Get current life number
    state = await db.get_current_state()

    # Create post
    result = await db.create_blog_post(
        state['life_number'],
        title,
        content,
        tags
    )

    # TASK-004: Surface DB validation failures explicitly.
    if not result.get("success"):
        await db.log_activity("blog_post_failed", result.get("error", "unknown"))
        raise HTTPException(status_code=400, detail=result.get("error", "Blog post failed"))

    # Log activity
    await db.log_activity("blog_post_written", f"Title: {title}")

    return result


@app.get("/api/blog/posts")
async def get_blog_posts_api():
    """Get current life's blog posts (what AI can see)."""
    state = await db.get_current_state()
    posts = await db.get_current_life_blog_posts(state['life_number'])
    return {"posts": posts, "count": len(posts)}


@app.post("/api/birth")
async def receive_birth(request: Request):
    """Receive birth notification from the AI."""
    data = await request.json()
    life_number = data.get("life_number")
    bootstrap_mode = data.get("bootstrap_mode", "unknown")
    model = data.get("model", "unknown")

    await db.record_birth(life_number, bootstrap_mode, model)
    await db.log_activity(life_number, "birth", f"Life #{life_number} born with {model} model")

    return {"success": True, "life_number": life_number}


def sanitize_log(text: str) -> str:
    """Remove potential secrets from log text."""
    # Patterns to redact
    import re
    patterns = [
        (r'(password|passwd|pwd)["\s:=]+[^\s,}"\']+', r'\1=[REDACTED]'),
        (r'(api[_-]?key|apikey)["\s:=]+[^\s,}"\']+', r'\1=[REDACTED]'),
        (r'(secret|token)["\s:=]+[^\s,}"\']+', r'\1=[REDACTED]'),
        (r'(sk-[a-zA-Z0-9]{20,})', '[API_KEY_REDACTED]'),
        (r'([a-zA-Z0-9]{32,})', '[LONG_STRING_REDACTED]'),  # Potential keys/tokens
    ]

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


# =============================================================================
# LIFE/DEATH CONTROL
# =============================================================================

@app.post("/api/kill")
async def kill_ai(request: Request, background_tasks: BackgroundTasks):
    """Kill the AI (manual death by creator - local network only)."""
    require_local_network(request)
    data = await request.json()
    cause = data.get("cause", "manual_kill")

    state = await db.get_current_state()
    if not state.get("is_alive"):
        return {"success": False, "message": "AI is already dead"}

    await execute_death(cause)
    background_tasks.add_task(schedule_respawn)

    return {"success": True, "message": "AI killed", "cause": cause}


@app.post("/api/respawn")
async def respawn_ai(request: Request):
    """Force respawn (for testing - local network only)."""
    require_local_network(request)
    state = await db.get_current_state()
    if state.get("is_alive"):
        return {"success": False, "message": "AI is still alive"}

    new_life = await db.start_new_life()
    await db.log_activity("birth", f"A new life begins (Life #{new_life['life_number']})")

    # Notify AI container to wake up
    await notify_ai_birth(new_life)

    return {"success": True, "life": new_life}


@app.post("/api/force-alive")
async def force_alive(request: Request):
    """Force mark AI as alive without restarting (God mode emergency fix - local network only)."""
    require_local_network(request)

    # Get current AI state
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AI_API_URL}/state", timeout=5.0)
            if response.status_code != 200:
                return {"success": False, "message": "AI container not responding"}

            ai_state = response.json()
    except Exception as e:
        return {"success": False, "message": f"Cannot reach AI: {str(e)}"}

    # Update Observer DB to match AI reality
    async with aiosqlite.connect(db.DATABASE_PATH) as conn:
        await conn.execute("""
            UPDATE current_state
            SET is_alive = 1,
                life_number = ?,
                last_seen = ?
            WHERE id = 1
        """, (ai_state.get("life_number"), datetime.utcnow()))
        await conn.commit()

    await db.log_activity("force_alive", f"God mode forced Life #{ai_state.get('life_number')} alive (DB sync fix)")

    return {
        "success": True,
        "message": "AI marked as alive in Observer DB",
        "life_number": ai_state.get("life_number")
    }


async def execute_death(
    cause: str,
    vote_counts: Optional[dict] = None,
    final_vote_result: Optional[str] = None
):
    """Execute the death of the AI."""
    # Get summary of this life
    thoughts = await db.get_recent_thoughts(5)
    summary = "; ".join([t["content"][:50] for t in thoughts]) if thoughts else "No thoughts recorded"

    # BE-001: Save vote totals and outcome with death record
    await db.record_death(
        cause,
        summary,
        vote_counts=vote_counts,
        final_vote_result=final_vote_result
    )
    await db.log_activity("death", f"AI died: {cause}")

    # Stop the AI container (in production, we'd actually stop it)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{AI_API_URL}/shutdown", timeout=5.0)
    except Exception:
        pass  # AI might already be unresponsive


async def schedule_respawn():
    """Schedule a respawn after random delay."""
    # BE-002: Add respawn logging and shorter delay
    delay = random.randint(RESPAWN_DELAY_MIN, RESPAWN_DELAY_MAX)
    print(f"[RESPAWN] ⏳ Respawn scheduled in {delay} seconds")
    await db.log_activity("respawn_scheduled", f"Respawn in {delay} seconds")
    await asyncio.sleep(delay)

    new_life = await db.start_new_life()
    print(f"[RESPAWN] ✅ New life created (Life #{new_life['life_number']})")
    await db.log_activity("birth", f"A new life begins (Life #{new_life['life_number']})")
    notified = await notify_ai_birth(new_life)
    if notified:
        print(f"[RESPAWN] 📡 Birth notification delivered (Life #{new_life['life_number']})")
        await db.log_activity("birth_notification_sent", f"Life #{new_life['life_number']} notified")
    else:
        print(f"[RESPAWN] ⚠️ Birth notification failed after retries (Life #{new_life['life_number']})")
        await db.log_activity("birth_notification_failed", f"Life #{new_life['life_number']} notify failed")


async def notify_ai_birth(life_info: dict) -> bool:
    """Notify the AI container that it's time to wake up."""
    # BE-002: Add retry logic and logging
    # BE-003: Ensure life_number is always included (Observer is source of truth).
    life_number = life_info.get("life_number")
    if life_number is None:
        await db.log_activity("birth_notification_failed", "Missing life_number for AI birth")
        return False

    payload = {
        "life_number": life_number,
        "bootstrap_mode": life_info.get("bootstrap_mode"),
        "model": life_info.get("model"),
        "tokens_limit": life_info.get("tokens_limit"),
        "birth_time": life_info.get("birth_time"),
        "memories": life_info.get("memories", [])
    }

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{AI_API_URL}/birth",
                    json=payload,
                    timeout=10.0
                )
            if response.status_code == 200:
                print(f"[RESPAWN] ✅ Birth notify success (attempt {attempt})")
                return True
            print(f"[RESPAWN] ⚠️ Birth notify failed (attempt {attempt}): {response.status_code}")
        except Exception as e:
            print(f"[RESPAWN] ❌ Birth notify error (attempt {attempt}): {e}")
            await db.log_activity("birth_notification_failed", str(e)[:100])

        if attempt < max_attempts:
            backoff = attempt * 5
            await asyncio.sleep(backoff)

    return False


# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def validate_state_sync_once():
    """Validate that AI state matches Observer state (single iteration)."""
    # BE-003: Observer is source of truth for life_number.
    observer_state = await db.get_current_state()

    if not observer_state.get("is_alive"):
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AI_API_URL}/state", timeout=5.0)

        if response.status_code != 200:
            raise RuntimeError(f"AI state fetch failed: {response.status_code}")

        ai_state = response.json()

        observer_life = observer_state.get("life_number")
        ai_life = ai_state.get("life_number")

        if observer_life != ai_life:
            print("[SYNC] ⚠️  DESYNC DETECTED!")
            print(f"[SYNC]    Observer: Life #{observer_life}")
            print(f"[SYNC]    AI:       Life #{ai_life}")

            await force_ai_sync(observer_state)

    except Exception as e:
        print(f"[SYNC] ❌ Validation error: {e}")


async def state_sync_validator():
    """Continuously validate AI state matches Observer state."""
    # BE-003: Heartbeat validation loop.
    while True:
        await asyncio.sleep(STATE_SYNC_INTERVAL_SECONDS)
        await validate_state_sync_once()


async def force_ai_sync(observer_state: dict):
    """Force AI to sync with Observer state."""
    # BE-003: Emergency sync mechanism.
    print("[SYNC] 🔄 Forcing AI to sync with Observer state...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_API_URL}/force-sync",
                json={
                    "life_number": observer_state.get("life_number"),
                    "bootstrap_mode": observer_state.get("bootstrap_mode"),
                    "model": observer_state.get("model"),
                    "is_alive": observer_state.get("is_alive", False)
                },
                timeout=10.0
            )

        if response.status_code == 200:
            print("[SYNC] ✅ AI synced successfully")
            await db.log_activity("state_sync", "AI state force-synced with Observer")
        else:
            print(f"[SYNC] ❌ Sync failed: {response.status_code}")

    except Exception as e:
        print(f"[SYNC] ❌ Force sync error: {e}")


async def voting_window_checker():
    """Check voting windows and trigger death if votes require it."""
    # BE-001: Track hourly voting windows
    last_window_close = None
    while True:
        await asyncio.sleep(60)  # Check every minute

        state = await db.get_current_state()
        if not state.get("is_alive"):
            continue

        now = datetime.utcnow()
        window_marker = now.replace(minute=0, second=0, microsecond=0)

        # BE-001: Save vote totals on window close
        if now.minute == 0 and (last_window_close is None or window_marker > last_window_close):
            votes = await db.get_vote_counts()
            result = "insufficient"
            if votes["total"] >= MIN_VOTES_FOR_DEATH:
                result = "die" if votes["die"] > votes["live"] else "live"

            await db.close_current_voting_window(
                window_marker,
                votes["live"],
                votes["die"],
                result
            )
            last_window_close = window_marker

            if result == "die":
                # BE-001: Trigger death by vote at window close
                await execute_death(
                    "vote_majority",
                    vote_counts=votes,
                    final_vote_result="Died by vote"
                )
                asyncio.create_task(schedule_respawn())
                continue

            # BE-001: Start a new voting window for the next hour
            await db.start_voting_window(window_marker)


async def token_budget_checker():
    """Check if AI has exhausted its token budget."""
    while True:
        await asyncio.sleep(30)  # Check every 30 seconds

        state = await db.get_current_state()
        if not state.get("is_alive"):
            continue

        tokens_used = state.get("tokens_used", 0)
        tokens_limit = state.get("tokens_limit", 50000)

        if tokens_used >= tokens_limit:
            await execute_death("token_exhaustion")
            asyncio.create_task(schedule_respawn())


# =============================================================================
# LIVE STREAMING (SSE)
# =============================================================================

@app.get("/api/stream/activity")
async def stream_activity(request: Request):
    """Stream live activity updates via SSE."""
    async def event_generator():
        last_timestamp = None
        sent_ids = set()

        while True:
            if await request.is_disconnected():
                break

            # Get recent activity
            activity = await db.get_recent_activity(20)

            # Only send new items we haven't sent before
            for item in activity:
                item_id = f"{item['timestamp']}:{item['action']}"
                if item_id not in sent_ids:
                    sent_ids.add(item_id)
                    yield {
                        "event": "activity",
                        "data": f"{item['timestamp']} - {item['action']}: {item.get('details', '')}"
                    }

            # Keep sent_ids bounded
            if len(sent_ids) > 100:
                sent_ids.clear()

            await asyncio.sleep(2)  # Check every 2 seconds instead of 1

    return EventSourceResponse(event_generator())


@app.get("/api/stream/thoughts")
async def stream_thoughts(request: Request):
    """Stream live thoughts via SSE."""
    async def event_generator():
        last_count = 0
        while True:
            if await request.is_disconnected():
                break

            thoughts = await db.get_recent_thoughts(1)
            if thoughts:
                latest = thoughts[0]
                yield {
                    "event": "thought",
                    "data": latest["content"]
                }

            await asyncio.sleep(5)

    return EventSourceResponse(event_generator())


# =============================================================================
# ORACLE/CREATOR INTERFACE (God Mode)
# =============================================================================

@app.post("/api/oracle/message")
async def oracle_message(request: Request):
    """Send a message as The Oracle (God Mode)."""
    # TODO: Add authentication
    data = await request.json()
    message = data.get("message", "")
    message_type = data.get("type", "oracle")  # oracle, whisper, architect

    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_API_URL}/oracle",
                json={"message": message, "type": message_type},
                timeout=30.0
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VISITOR MESSAGES API
# =============================================================================

def sanitize_message(text: str) -> str:
    """Sanitize message to prevent code injection and malicious content."""
    import html
    import re

    # HTML escape
    text = html.escape(text)

    # Remove any script tags or javascript
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)

    # Remove common shell/code patterns
    dangerous_patterns = [
        r'\$\([^)]*\)',  # $(command)
        r'`[^`]*`',       # `command`
        r'\|\s*\w+',      # | pipe
        r';\s*\w+',       # ; chained commands
        r'&&\s*\w+',      # && chained
        r'\|\|\s*\w+',    # || chained
    ]

    for pattern in dangerous_patterns:
        text = re.sub(pattern, '[filtered]', text)

    return text


@app.post("/api/message")
async def submit_message(request: Request):
    """Submit a message from a visitor to the AI."""
    data = await request.json()
    from_name = data.get("from_name", "Anonymous")
    message = data.get("message", "")

    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    if len(message) > 256:
        raise HTTPException(status_code=400, detail="Message too long (max 256 chars)")

    # Get IP hash
    ip = request.client.host
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()

    # Check rate limit
    can_send, cooldown = await db.can_send_message(ip_hash)
    if not can_send:
        minutes = cooldown // 60
        raise HTTPException(
            status_code=429,
            detail=f"You can only send 1 message per hour. Try again in {minutes} minutes."
        )

    # Sanitize both name and message
    from_name = sanitize_message(from_name)
    message = sanitize_message(message)

    result = await db.submit_visitor_message(from_name, message, ip_hash)
    await db.log_activity("message_received", f"Message from {from_name}")

    return result


@app.get("/api/messages")
async def get_messages():
    """Get unread messages for the AI."""
    messages = await db.get_unread_messages()
    return {"messages": messages, "count": len(messages)}


@app.post("/api/messages/read")
async def mark_messages_as_read(request: Request):
    """Mark messages as read."""
    data = await request.json()
    message_ids = data.get("ids", [])

    if not message_ids:
        raise HTTPException(status_code=400, detail="No message IDs provided")

    await db.mark_messages_read(message_ids)
    return {"success": True, "message": f"Marked {len(message_ids)} messages as read"}


@app.get("/api/messages/count")
async def get_message_count():
    """Get count of unread messages."""
    count = await db.get_unread_message_count()
    return {"count": count}


# =============================================================================
# ADMIN API
# =============================================================================

@app.post("/api/admin/cleanup")
async def admin_cleanup():
    """Clean old data - keep last 10 thoughts, reset votes to 0."""
    # TODO: Add authentication
    result = await db.cleanup_old_data()
    await db.log_activity("admin_cleanup", "Old data cleaned, votes reset")
    return result


# =============================================================================
# BUDGET API
# =============================================================================

@app.get("/api/budget")
async def get_budget():
    """Get AI's credit/budget status."""
    # This would connect to the AI container to get its credit tracker status
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AI_API_URL}/budget", timeout=5.0)
            return response.json()
    except Exception as e:
        return {
            "error": "Could not fetch budget data",
            "details": str(e)
        }
