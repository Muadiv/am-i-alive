from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "observer_v2"


def test_home_page_renders(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Am I Alive v2" in response.text
    assert "Vote live" in response.text
    assert "Vote die" in response.text
    assert "Showing latest meaningful updates." in response.text
    assert "Current move" in response.text


def test_public_state_shape(client: TestClient) -> None:
    response = client.get("/api/public/state")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["is_alive"] is True
    assert data["state"] == "active"
    assert "updated_at" in data
