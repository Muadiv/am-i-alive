from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

from .config import Config
from .intention_engine import IntentionEngine
from .moments import MomentsStore
from .storage import SqliteStorage
from .vote_rounds import VoteRoundService
from .web import index_html


def register_routes(
    app: FastAPI,
    storage: SqliteStorage,
    vote_round_service: VoteRoundService,
    intention_engine: IntentionEngine,
    moments_store: MomentsStore,
    check_vote_rounds_once: Callable[[], Awaitable[dict[str, object]]],
    sync_funding_once: Callable[[], Awaitable[dict[str, object]]],
    tick_intention_once: Callable[[], Awaitable[dict[str, object] | None]],
) -> None:
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "observer_v2"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse(content=index_html())

    @app.get("/api/public/state")
    async def public_state() -> dict[str, object]:
        state = storage.get_life_state()
        return {
            "success": True,
            "data": {
                "life_number": state["life_number"],
                "is_alive": state["is_alive"],
                "state": state["state"],
                "current_intention": state["current_intention"],
                "updated_at": state["updated_at"],
            },
        }

    @app.get("/api/public/vote-round")
    async def public_vote_round() -> dict[str, object]:
        vote_round = storage.get_open_vote_round()
        return {"success": True, "data": vote_round}

    @app.post("/api/public/vote")
    async def submit_vote(request: Request, payload: dict[str, object]) -> dict[str, object]:
        state = storage.get_life_state()
        if not bool(state["is_alive"]):
            raise HTTPException(status_code=409, detail="Voting is closed while organism is dead")

        vote = str(payload.get("vote", "")).strip().lower()
        reason = str(payload.get("reason", "")).strip()
        voter_fingerprint = request.client.host if request.client else "unknown"
        try:
            result = vote_round_service.cast_vote(voter_fingerprint=voter_fingerprint, vote=vote, reason=reason)
        except ValueError as exc:
            message = str(exc)
            status_code = 429 if "already voted" in message else 400
            raise HTTPException(status_code=status_code, detail=message) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"success": True, "data": result}

    @app.get("/api/public/funding")
    async def public_funding() -> dict[str, object]:
        donations = storage.list_donations(limit=10)
        return {
            "success": True,
            "data": {
                "btc_address": Config.DONATION_BTC_ADDRESS,
                "donations": donations,
            },
        }

    @app.get("/api/public/intention")
    async def public_intention() -> dict[str, object]:
        active = intention_engine.get_active_intention()
        return {"success": True, "data": active}

    @app.get("/api/public/intentions")
    async def public_intentions(limit: int = 20) -> dict[str, object]:
        safe_limit = max(1, min(limit, 100))
        intentions = intention_engine.list_recent(limit=safe_limit)
        return {"success": True, "data": intentions}

    @app.get("/api/public/timeline")
    async def public_timeline(limit: int = 30) -> dict[str, object]:
        safe_limit = max(1, min(limit, 100))
        timeline = moments_store.list_public(limit=safe_limit)
        return {"success": True, "data": timeline}

    @app.post("/api/internal/funding/donation")
    async def ingest_donation(
        payload: dict[str, object],
        x_internal_key: str | None = Header(default=None),
    ) -> dict[str, object]:
        _require_internal_auth(x_internal_key)

        txid = str(payload.get("txid", "")).strip()
        amount_btc = float(payload.get("amount_btc", 0.0))
        confirmations = int(payload.get("confirmations", 0))

        if not txid:
            raise HTTPException(status_code=400, detail="txid is required")
        if amount_btc <= 0:
            raise HTTPException(status_code=400, detail="amount_btc must be positive")
        if confirmations < 0:
            raise HTTPException(status_code=400, detail="confirmations must be non-negative")

        donation = storage.upsert_donation(txid=txid, amount_btc=amount_btc, confirmations=confirmations)
        state = storage.get_life_state()
        moments_store.add_moment(
            life_number=int(state["life_number"]),
            moment_type="funding",
            title="Donation recorded",
            content=f"Donation {txid} recorded with {confirmations} confirmations.",
        )
        return {"success": True, "data": donation}

    @app.post("/api/internal/vote-rounds/close")
    async def close_vote_round(x_internal_key: str | None = Header(default=None)) -> dict[str, object]:
        _require_internal_auth(x_internal_key)
        result = await check_vote_rounds_once()
        open_round = None
        try:
            open_round = storage.get_open_vote_round()
        except RuntimeError:
            open_round = None
        return {"success": True, "data": {"result": result, "open_round": open_round}}

    @app.post("/api/internal/funding/sync")
    async def sync_funding(x_internal_key: str | None = Header(default=None)) -> dict[str, object]:
        _require_internal_auth(x_internal_key)
        result = await sync_funding_once()
        return {"success": bool(result.get("success", False)), "data": result}

    @app.post("/api/internal/intention/tick")
    async def tick_intention(x_internal_key: str | None = Header(default=None)) -> dict[str, object]:
        _require_internal_auth(x_internal_key)
        intention = await tick_intention_once()
        return {"success": True, "data": intention}

    @app.post("/api/internal/intention/close")
    async def close_intention(
        payload: dict[str, object],
        x_internal_key: str | None = Header(default=None),
    ) -> dict[str, object]:
        _require_internal_auth(x_internal_key)
        outcome = str(payload.get("outcome", "")).strip() or "closed_manually"
        closed = intention_engine.close_active(outcome=outcome)
        if closed:
            state = storage.get_life_state()
            moments_store.add_moment(
                life_number=int(state["life_number"]),
                moment_type="intention",
                title="Intention closed",
                content=f"{closed['kind']} closed with outcome: {outcome}",
            )
        return {"success": True, "data": closed}

    @app.post("/api/internal/lifecycle/transition")
    async def transition_lifecycle(
        payload: dict[str, object],
        x_internal_key: str | None = Header(default=None),
    ) -> dict[str, object]:
        _require_internal_auth(x_internal_key)

        next_state = str(payload.get("next_state", "")).strip()
        current_intention = str(payload.get("current_intention", "")).strip() or None
        death_cause = str(payload.get("death_cause", "")).strip() or None
        if not next_state:
            raise HTTPException(status_code=400, detail="next_state is required")

        try:
            state = storage.transition_life_state(
                next_state=next_state,
                current_intention=current_intention,
                death_cause=death_cause,
            )
            if next_state == "born":
                vote_round_service.reset_rounds_for_new_life()
                intention_engine.close_active(outcome="rebirth_reset")
                intention_engine.tick(is_alive=True)
                moments_store.add_moment(
                    life_number=int(state["life_number"]),
                    moment_type="rebirth",
                    title="New life started",
                    content="Lifecycle transitioned to born and systems reinitialized.",
                )
            if next_state == "dead":
                intention_engine.close_active(outcome="life_ended")
                moments_store.add_moment(
                    life_number=int(state["life_number"]),
                    moment_type="death",
                    title="Life ended",
                    content=f"Death cause registered: {death_cause or 'unknown'}.",
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {"success": True, "data": state}


def _require_internal_auth(x_internal_key: str | None) -> None:
    if Config.INTERNAL_API_KEY and x_internal_key != Config.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
