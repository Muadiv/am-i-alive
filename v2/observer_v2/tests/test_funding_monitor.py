from __future__ import annotations

from pathlib import Path

from observer_v2.funding_monitor import FundingMonitor
from observer_v2.storage import SqliteStorage


class FakeExplorerClient:
    def __init__(self, transactions: list[dict[str, object]]) -> None:
        self.transactions = transactions

    def fetch_address_transactions(self, address: str) -> list[dict[str, object]]:
        del address
        return self.transactions


def test_funding_monitor_skips_when_address_missing(tmp_path: Path) -> None:
    storage = SqliteStorage(str(tmp_path / "monitor.db"))
    storage.init_schema()
    storage.bootstrap_defaults()
    monitor = FundingMonitor(
        storage=storage,
        donation_address="",
        explorer_client=FakeExplorerClient([]),
    )

    result = monitor.sync_once()
    assert result["success"] is True
    assert result["skipped"] is True


def test_funding_monitor_imports_matching_address_outputs(tmp_path: Path) -> None:
    storage = SqliteStorage(str(tmp_path / "monitor_import.db"))
    storage.init_schema()
    storage.bootstrap_defaults()
    transactions = [
        {
            "txid": "txmatch",
            "status": {"confirmed": True},
            "vout": [
                {"scriptpubkey_address": "bc1_test", "value": 150000},
                {"scriptpubkey_address": "other", "value": 1000},
            ],
        }
    ]
    monitor = FundingMonitor(
        storage=storage,
        donation_address="bc1_test",
        explorer_client=FakeExplorerClient(transactions),
    )

    result = monitor.sync_once()
    assert result["success"] is True
    assert result["imported"] == 1

    donations = storage.list_donations()
    assert donations[0]["txid"] == "txmatch"
    assert donations[0]["status"] == "confirmed"
    assert donations[0]["amount_btc"] == 0.0015
