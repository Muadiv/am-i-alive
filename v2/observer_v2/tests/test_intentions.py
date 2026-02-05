from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from observer_v2.intention_engine import IntentionEngine
from observer_v2.storage import SqliteStorage


def test_intention_engine_bootstrap_creates_active(tmp_path: Path) -> None:
    storage = SqliteStorage(str(tmp_path / "intentions.db"))
    storage.init_schema()
    storage.bootstrap_defaults()

    engine = IntentionEngine(storage.database_path)
    engine.init_schema()
    engine.bootstrap_defaults()

    active = engine.get_active_intention()
    assert active is not None
    assert active["status"] == "active"


def test_public_intention_endpoint(client: TestClient) -> None:
    response = client.get("/api/public/intention")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"] is not None


def test_close_and_tick_intention_endpoints(client: TestClient) -> None:
    close_response = client.post("/api/internal/intention/close", json={"outcome": "completed"})
    assert close_response.status_code == 200
    close_payload = close_response.json()["data"]
    assert close_payload["status"] == "closed"

    tick_response = client.post("/api/internal/intention/tick")
    assert tick_response.status_code == 200
    tick_payload = tick_response.json()["data"]
    assert tick_payload["status"] == "active"


def test_dead_lifecycle_closes_active_intention(client: TestClient) -> None:
    client.post("/api/internal/lifecycle/transition", json={"next_state": "dying"})
    client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "dead", "death_cause": "bankruptcy"},
    )
    recent_response = client.get("/api/public/intentions")
    recent = recent_response.json()["data"]
    assert recent[0]["status"] == "closed"
    assert recent[0]["outcome"] == "life_ended"
