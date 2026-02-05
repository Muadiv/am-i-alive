from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import request

from .storage import SqliteStorage


def _sats_to_btc(sats: int) -> float:
    return sats / 100_000_000


@dataclass
class WalletExplorerClient:
    api_base: str
    timeout_seconds: int = 10

    def fetch_address_transactions(self, address: str) -> list[dict[str, object]]:
        url = f"{self.api_base}/address/{address}/txs"
        with request.urlopen(url, timeout=self.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        parsed = json.loads(payload)
        if not isinstance(parsed, list):
            return []
        return [item for item in parsed if isinstance(item, dict)]


@dataclass
class FundingMonitor:
    storage: SqliteStorage
    donation_address: str
    explorer_client: WalletExplorerClient

    def sync_once(self) -> dict[str, object]:
        address = self.donation_address.strip()
        if not address:
            return {"success": True, "skipped": True, "reason": "missing_address"}

        transactions = self.explorer_client.fetch_address_transactions(address)
        imported = 0
        for transaction in transactions:
            txid = str(transaction.get("txid", "")).strip()
            if not txid:
                continue
            amount_sats = self._extract_received_sats(transaction, address)
            if amount_sats <= 0:
                continue

            status_payload = transaction.get("status", {})
            confirmed = bool(status_payload.get("confirmed", False)) if isinstance(status_payload, dict) else False
            confirmations = 1 if confirmed else 0
            self.storage.upsert_donation(
                txid=txid,
                amount_btc=_sats_to_btc(amount_sats),
                confirmations=confirmations,
            )
            imported += 1

        return {"success": True, "scanned": len(transactions), "imported": imported}

    def _extract_received_sats(self, transaction: dict[str, object], address: str) -> int:
        vout = transaction.get("vout", [])
        if not isinstance(vout, list):
            return 0

        received = 0
        for output in vout:
            if not isinstance(output, dict):
                continue
            output_address = str(output.get("scriptpubkey_address", "")).strip()
            if output_address != address:
                continue
            output_value = output.get("value", 0)
            if isinstance(output_value, int):
                received += output_value
        return received
