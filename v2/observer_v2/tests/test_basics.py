from __future__ import annotations

from fastapi.testclient import TestClient

from observer_v2.app import app


def test_health_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "observer_v2"


def test_public_state_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/public/state")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["is_alive"] is True
    assert data["state"] == "active"
    assert "updated_at" in data
