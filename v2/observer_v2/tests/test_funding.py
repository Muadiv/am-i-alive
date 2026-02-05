from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from observer_v2.storage import SqliteStorage


def test_ledger_is_idempotent_by_txid(tmp_path: Path) -> None:
    ledger = SqliteStorage(str(tmp_path / "funding.db"))
    ledger.init_schema()
    ledger.bootstrap_defaults()
    first = ledger.upsert_donation("tx1", 0.001, confirmations=0)
    second = ledger.upsert_donation("tx1", 0.001, confirmations=2)
    assert first["txid"] == second["txid"]
    assert second["confirmations"] == 2
    assert second["status"] == "confirmed"
    assert len(ledger.list_donations()) == 1


def test_public_funding_endpoint_shape(client: TestClient) -> None:
    response = client.get("/api/public/funding")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "btc_address" in payload["data"]
    assert "donations" in payload["data"]


def test_ingest_donation_persists_data(client: TestClient) -> None:
    response = client.post(
        "/api/internal/funding/donation",
        json={"txid": "tx_api_1", "amount_btc": 0.005, "confirmations": 1},
    )
    assert response.status_code == 200

    funding_response = client.get("/api/public/funding")
    assert funding_response.status_code == 200
    payload = funding_response.json()["data"]["donations"]
    assert payload[0]["txid"] == "tx_api_1"
    assert payload[0]["status"] == "confirmed"
