from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sqlite3

from .voting import ROUND_DURATION_HOURS


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SqliteStorage:
    database_path: str

    def init_schema(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS life_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    life_number INTEGER NOT NULL,
                    is_alive INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    current_intention TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vote_rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    starts_at TEXT NOT NULL,
                    ends_at TEXT NOT NULL,
                    live_count INTEGER NOT NULL,
                    die_count INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS donations (
                    txid TEXT PRIMARY KEY,
                    amount_btc REAL NOT NULL,
                    confirmations INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    seen_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def bootstrap_defaults(self) -> None:
        self._ensure_life_state()
        self._ensure_open_vote_round()

    def get_life_state(self) -> dict[str, object]:
        self._ensure_life_state()
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute(
                """
                SELECT life_number, is_alive, state, current_intention, updated_at
                FROM life_state
                WHERE id = 1
                """
            ).fetchone()
        if not row:
            raise RuntimeError("life_state row missing")
        return {
            "life_number": int(row[0]),
            "is_alive": bool(row[1]),
            "state": str(row[2]),
            "current_intention": str(row[3]),
            "updated_at": str(row[4]),
        }

    def get_open_vote_round(self) -> dict[str, object]:
        self._ensure_open_vote_round()
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute(
                """
                SELECT id, starts_at, ends_at, live_count, die_count, status
                FROM vote_rounds
                WHERE status = 'open'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            raise RuntimeError("open vote round missing")
        return {
            "id": int(row[0]),
            "starts_at": str(row[1]),
            "ends_at": str(row[2]),
            "live": int(row[3]),
            "die": int(row[4]),
            "status": str(row[5]),
        }

    def upsert_donation(self, txid: str, amount_btc: float, confirmations: int) -> dict[str, object]:
        if not txid:
            raise ValueError("txid is required")
        status = "confirmed" if confirmations >= 1 else "pending"

        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute(
                "SELECT txid, amount_btc, confirmations, status, seen_at FROM donations WHERE txid = ?",
                (txid,),
            ).fetchone()

            if row:
                next_confirmations = max(int(row[2]), confirmations)
                next_status = "confirmed" if next_confirmations >= 1 else "pending"
                conn.execute(
                    "UPDATE donations SET confirmations = ?, status = ? WHERE txid = ?",
                    (next_confirmations, next_status, txid),
                )
                conn.commit()
                return {
                    "txid": txid,
                    "amount_btc": float(row[1]),
                    "confirmations": next_confirmations,
                    "status": next_status,
                    "seen_at": str(row[4]),
                }

            seen_at = utc_now_iso()
            conn.execute(
                """
                INSERT INTO donations (txid, amount_btc, confirmations, status, seen_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (txid, amount_btc, confirmations, status, seen_at),
            )
            conn.commit()
            return {
                "txid": txid,
                "amount_btc": amount_btc,
                "confirmations": confirmations,
                "status": status,
                "seen_at": seen_at,
            }

    def list_donations(self, limit: int = 20) -> list[dict[str, object]]:
        with sqlite3.connect(self.database_path) as conn:
            rows = conn.execute(
                """
                SELECT txid, amount_btc, confirmations, status, seen_at
                FROM donations
                ORDER BY seen_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "txid": str(row[0]),
                "amount_btc": float(row[1]),
                "confirmations": int(row[2]),
                "status": str(row[3]),
                "seen_at": str(row[4]),
            }
            for row in rows
        ]

    def _ensure_life_state(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute("SELECT id FROM life_state WHERE id = 1").fetchone()
            if row:
                return
            conn.execute(
                """
                INSERT INTO life_state (id, life_number, is_alive, state, current_intention, updated_at)
                VALUES (1, 1, 1, 'active', 'bootstrap', ?)
                """,
                (utc_now_iso(),),
            )
            conn.commit()

    def _ensure_open_vote_round(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute("SELECT id FROM vote_rounds WHERE status = 'open' LIMIT 1").fetchone()
            if row:
                return
            starts_at = datetime.now(timezone.utc)
            ends_at = starts_at + timedelta(hours=ROUND_DURATION_HOURS)
            conn.execute(
                """
                INSERT INTO vote_rounds (starts_at, ends_at, live_count, die_count, status)
                VALUES (?, ?, 0, 0, 'open')
                """,
                (starts_at.isoformat(), ends_at.isoformat()),
            )
            conn.commit()
