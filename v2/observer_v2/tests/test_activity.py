from __future__ import annotations

from fastapi.testclient import TestClient

from observer_v2.activity_engine import ActivityEngine


def test_activity_engine_returns_structured_update() -> None:
    engine = ActivityEngine(minimum_interval_seconds=420)
    title, content = engine.build_activity(
        intention_kind="survive",
        live_votes=1,
        die_votes=0,
        donations_count=0,
        sequence=0,
    )
    assert title
    assert "Intent:" in content
    assert "Action:" in content
    assert "Result:" in content
    assert "Next:" in content


def test_public_activity_endpoint(client: TestClient) -> None:
    response = client.get("/api/public/activity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True


def test_forced_activity_tick_creates_activity_moment(client: TestClient) -> None:
    response = client.post("/api/internal/activity/tick", json={"force": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"] is not None
    assert payload["data"]["moment_type"] == "activity"
