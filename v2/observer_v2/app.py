from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI

from .config import Config
from .funding import DonationLedger


def create_app() -> FastAPI:
    app = FastAPI(title=Config.APP_NAME, version=Config.APP_VERSION)
    donation_ledger = DonationLedger()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "observer_v2"}

    @app.get("/api/public/state")
    async def public_state() -> dict[str, object]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "success": True,
            "data": {
                "life_number": 1,
                "is_alive": True,
                "state": "active",
                "current_intention": "bootstrap",
                "updated_at": now,
            },
        }

    @app.get("/api/public/funding")
    async def public_funding() -> dict[str, object]:
        donations = [d.__dict__ for d in donation_ledger.recent(limit=10)]
        return {
            "success": True,
            "data": {
                "btc_address": Config.DONATION_BTC_ADDRESS,
                "donations": donations,
            },
        }

    return app


app = create_app()
