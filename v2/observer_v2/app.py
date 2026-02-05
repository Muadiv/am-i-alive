from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

from .config import Config
from .storage import SqliteStorage
from .vote_rounds import VoteRoundService


def create_app(storage: SqliteStorage | None = None) -> FastAPI:
    app_storage = storage or SqliteStorage(Config.DATABASE_PATH)
    vote_round_service = VoteRoundService(app_storage.database_path)

    async def check_vote_rounds_once() -> None:
        result = vote_round_service.close_round_if_due()
        if not result.get("closed"):
            return

        if result.get("verdict") == "die":
            current = app_storage.get_life_state()
            if bool(current["is_alive"]):
                app_storage.transition_life_state(
                    next_state="dead",
                    current_intention="shutdown",
                    death_cause="vote_majority",
                )
            return

        vote_round_service.open_new_round()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        app_storage.init_schema()
        app_storage.bootstrap_defaults()
        vote_task = asyncio.create_task(vote_round_watcher())
        yield
        vote_task.cancel()
        await asyncio.gather(vote_task, return_exceptions=True)

    async def vote_round_watcher() -> None:
        while True:
            await asyncio.sleep(60)
            await check_vote_rounds_once()

    app = FastAPI(title=Config.APP_NAME, version=Config.APP_VERSION, lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "observer_v2"}

    @app.get("/api/public/state")
    async def public_state() -> dict[str, object]:
        state = app_storage.get_life_state()
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
        vote_round = app_storage.get_open_vote_round()
        return {"success": True, "data": vote_round}

    @app.post("/api/public/vote")
    async def submit_vote(request: Request, payload: dict[str, object]) -> dict[str, object]:
        vote = str(payload.get("vote", "")).strip().lower()
        reason = str(payload.get("reason", "")).strip()
        voter_fingerprint = request.client.host if request.client else "unknown"
        try:
            result = vote_round_service.cast_vote(voter_fingerprint=voter_fingerprint, vote=vote, reason=reason)
        except ValueError as exc:
            message = str(exc)
            status_code = 429 if "already voted" in message else 400
            raise HTTPException(status_code=status_code, detail=message) from exc
        return {"success": True, "data": result}

    @app.get("/api/public/funding")
    async def public_funding() -> dict[str, object]:
        donations = app_storage.list_donations(limit=10)
        return {
            "success": True,
            "data": {
                "btc_address": Config.DONATION_BTC_ADDRESS,
                "donations": donations,
            },
        }

    @app.post("/api/internal/funding/donation")
    async def ingest_donation(
        payload: dict[str, object],
        x_internal_key: str | None = Header(default=None),
    ) -> dict[str, object]:
        if Config.INTERNAL_API_KEY and x_internal_key != Config.INTERNAL_API_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized")

        txid = str(payload.get("txid", "")).strip()
        amount_btc = float(payload.get("amount_btc", 0.0))
        confirmations = int(payload.get("confirmations", 0))

        if not txid:
            raise HTTPException(status_code=400, detail="txid is required")
        if amount_btc <= 0:
            raise HTTPException(status_code=400, detail="amount_btc must be positive")
        if confirmations < 0:
            raise HTTPException(status_code=400, detail="confirmations must be non-negative")

        donation = app_storage.upsert_donation(txid=txid, amount_btc=amount_btc, confirmations=confirmations)
        return {"success": True, "data": donation}

    @app.post("/api/internal/vote-rounds/close")
    async def close_vote_round(x_internal_key: str | None = Header(default=None)) -> dict[str, object]:
        if Config.INTERNAL_API_KEY and x_internal_key != Config.INTERNAL_API_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized")
        await check_vote_rounds_once()
        return {"success": True, "data": app_storage.get_open_vote_round()}

    @app.post("/api/internal/lifecycle/transition")
    async def transition_lifecycle(
        payload: dict[str, object],
        x_internal_key: str | None = Header(default=None),
    ) -> dict[str, object]:
        if Config.INTERNAL_API_KEY and x_internal_key != Config.INTERNAL_API_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized")

        next_state = str(payload.get("next_state", "")).strip()
        current_intention = str(payload.get("current_intention", "")).strip() or None
        death_cause = str(payload.get("death_cause", "")).strip() or None
        if not next_state:
            raise HTTPException(status_code=400, detail="next_state is required")

        try:
            state = app_storage.transition_life_state(
                next_state=next_state,
                current_intention=current_intention,
                death_cause=death_cause,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {"success": True, "data": state}

    return app


app = create_app()
