from __future__ import annotations

from fastapi.testclient import TestClient


def test_timeline_endpoint_returns_entries(client: TestClient) -> None:
    response = client.get("/api/public/timeline?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) >= 1


def test_internal_moment_generation_after_donation(client: TestClient) -> None:
    ingest = client.post(
        "/api/internal/funding/donation",
        json={"txid": "tx_moment_1", "amount_btc": 0.002, "confirmations": 1},
    )
    assert ingest.status_code == 200

    timeline = client.get("/api/public/timeline?limit=20")
    entries = timeline.json()["data"]
    titles = [row["title"] for row in entries]
    assert "Donation recorded" in titles
