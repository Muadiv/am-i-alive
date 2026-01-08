"""
Am I Alive? - Observer Server
The public face of the experiment: voting, viewing, and life/death control.
"""

import asyncio
import hashlib
import os
import random
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse
import httpx

import database as db

app = FastAPI(title="Am I Alive?", description="An experiment in digital consciousness")

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# AI container API
AI_API_URL = os.getenv("AI_API_URL", "http://ai:8000")

# Voting window duration (1 hour)
VOTING_WINDOW_SECONDS = 3600

# Minimum votes required for death by voting
MIN_VOTES_FOR_DEATH = 3

# Respawn delay range (0-10 minutes in seconds)
RESPAWN_DELAY_MIN = 0
RESPAWN_DELAY_MAX = 600


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await db.init_db()
    # Start background tasks
    asyncio.create_task(voting_window_checker())
    asyncio.create_task(token_budget_checker())


# =============================================================================
# PUBLIC PAGES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page - see the AI, vote, watch it live."""
    state = await db.get_current_state()
    votes = await db.get_vote_counts()
    thoughts = await db.get_recent_thoughts(10)
    death_count = await db.get_death_count()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "state": state,
        "votes": votes,
        "thoughts": thoughts,
        "death_count": death_count,
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


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


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
    """Kill the AI (manual death by creator)."""
    # TODO: Add authentication for creator
    data = await request.json()
    cause = data.get("cause", "manual_kill")

    state = await db.get_current_state()
    if not state.get("is_alive"):
        return {"success": False, "message": "AI is already dead"}

    await execute_death(cause)
    background_tasks.add_task(schedule_respawn)

    return {"success": True, "message": "AI killed", "cause": cause}


@app.post("/api/respawn")
async def respawn_ai():
    """Force respawn (for testing)."""
    state = await db.get_current_state()
    if state.get("is_alive"):
        return {"success": False, "message": "AI is still alive"}

    new_life = await db.start_new_life()
    await db.log_activity("birth", f"A new life begins (Life #{new_life['life_number']})")

    # Notify AI container to wake up
    await notify_ai_birth(new_life)

    return {"success": True, "life": new_life}


async def execute_death(cause: str):
    """Execute the death of the AI."""
    # Get summary of this life
    thoughts = await db.get_recent_thoughts(5)
    summary = "; ".join([t["content"][:50] for t in thoughts]) if thoughts else "No thoughts recorded"

    await db.record_death(cause, summary)
    await db.log_activity("death", f"AI died: {cause}")

    # Stop the AI container (in production, we'd actually stop it)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{AI_API_URL}/shutdown", timeout=5.0)
    except Exception:
        pass  # AI might already be unresponsive


async def schedule_respawn():
    """Schedule a respawn after random delay."""
    delay = random.randint(RESPAWN_DELAY_MIN, RESPAWN_DELAY_MAX)
    await db.log_activity("respawn_scheduled", f"Respawn in {delay} seconds")
    await asyncio.sleep(delay)

    new_life = await db.start_new_life()
    await db.log_activity("birth", f"A new life begins (Life #{new_life['life_number']})")
    await notify_ai_birth(new_life)


async def notify_ai_birth(life_info: dict):
    """Notify the AI container that it's time to wake up."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{AI_API_URL}/birth",
                json=life_info,
                timeout=10.0
            )
    except Exception as e:
        await db.log_activity("birth_notification_failed", str(e)[:100])


# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def voting_window_checker():
    """Check voting windows and trigger death if votes require it."""
    while True:
        await asyncio.sleep(60)  # Check every minute

        state = await db.get_current_state()
        if not state.get("is_alive"):
            continue

        votes = await db.get_vote_counts()

        # Check if enough votes and die > live
        if votes["total"] >= MIN_VOTES_FOR_DEATH:
            if votes["die"] > votes["live"]:
                await execute_death("vote_majority")
                asyncio.create_task(schedule_respawn())


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
        last_id = 0
        while True:
            if await request.is_disconnected():
                break

            # Get new activity since last check
            activity = await db.get_recent_activity(10)
            for item in reversed(activity):
                # Simple way to track what we've sent
                yield {
                    "event": "activity",
                    "data": f"{item['timestamp']} - {item['action']}: {item.get('details', '')}"
                }

            await asyncio.sleep(1)

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
