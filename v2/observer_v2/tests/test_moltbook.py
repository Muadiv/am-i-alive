from __future__ import annotations

from fastapi.testclient import TestClient


def test_internal_moltbook_publish_returns_missing_key_without_config(client: TestClient) -> None:
    response = client.post("/api/internal/moltbook/publish", json={"force": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["data"]["error"] == "missing_api_key"
