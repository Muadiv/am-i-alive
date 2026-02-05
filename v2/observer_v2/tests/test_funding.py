from __future__ import annotations

from fastapi.testclient import TestClient

from observer_v2.app import app
from observer_v2.funding import DonationLedger


def test_ledger_is_idempotent_by_txid() -> None:
    ledger = DonationLedger()
    first = ledger.add_or_update("tx1", 0.001, confirmations=0)
    second = ledger.add_or_update("tx1", 0.001, confirmations=2)
    assert first.txid == second.txid
    assert second.confirmations == 2
    assert second.status == "confirmed"
    assert len(ledger.recent()) == 1


def test_public_funding_endpoint_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/public/funding")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "btc_address" in payload["data"]
    assert "donations" in payload["data"]
