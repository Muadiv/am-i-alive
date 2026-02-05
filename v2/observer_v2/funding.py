from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Donation:
    txid: str
    amount_btc: float
    confirmations: int = 0
    status: str = "pending"
    seen_at: str = ""


class DonationLedger:
    def __init__(self) -> None:
        self._donations: dict[str, Donation] = {}

    def add_or_update(self, txid: str, amount_btc: float, confirmations: int) -> Donation:
        now = datetime.now(timezone.utc).isoformat()
        status = "confirmed" if confirmations >= 1 else "pending"
        if txid in self._donations:
            donation = self._donations[txid]
            donation.confirmations = max(donation.confirmations, confirmations)
            donation.status = "confirmed" if donation.confirmations >= 1 else "pending"
            return donation

        donation = Donation(
            txid=txid,
            amount_btc=amount_btc,
            confirmations=confirmations,
            status=status,
            seen_at=now,
        )
        self._donations[txid] = donation
        return donation

    def recent(self, limit: int = 20) -> list[Donation]:
        rows = sorted(self._donations.values(), key=lambda d: d.seen_at, reverse=True)
        return rows[:limit]
