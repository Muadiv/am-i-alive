from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException

from .config import Config
from .storage import SqliteStorage


def create_app(storage: SqliteStorage | None = None) -> FastAPI:
    app = FastAPI(title=Config.APP_NAME, version=Config.APP_VERSION)
    app_storage = storage or SqliteStorage(Config.DATABASE_PATH)

    @app.on_event("startup")
    async def startup() -> None:
        app_storage.init_schema()
        app_storage.bootstrap_defaults()

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

    return app


app = create_app()
