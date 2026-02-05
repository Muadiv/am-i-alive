from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI

from .config import Config


def create_app() -> FastAPI:
    app = FastAPI(title=Config.APP_NAME, version=Config.APP_VERSION)

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

    return app


app = create_app()
