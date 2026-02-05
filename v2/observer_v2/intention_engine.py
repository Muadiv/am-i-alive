from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3


INTENTION_SEQUENCE = ["survive", "create", "investigate", "connect", "fundraise"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IntentionEngine:
    database_path: str

    def init_schema(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS intentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    life_number INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    status TEXT NOT NULL,
                    outcome TEXT,
                    started_at TEXT NOT NULL,
                    closed_at TEXT
                )
                """
            )
            conn.commit()

    def bootstrap_defaults(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute("SELECT id FROM intentions WHERE status = 'active' LIMIT 1").fetchone()
            if row:
                return
        self.tick(is_alive=True)

    def tick(self, is_alive: bool) -> dict[str, object] | None:
        if not is_alive:
            return None

        active = self.get_active_intention()
        if active:
            return active

        with sqlite3.connect(self.database_path) as conn:
            life_row = conn.execute("SELECT life_number FROM life_state WHERE id = 1").fetchone()
            if not life_row:
                raise RuntimeError("life_state row missing")
            life_number = int(life_row[0])

            last_closed_row = conn.execute(
                """
                SELECT kind FROM intentions
                WHERE status = 'closed'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            next_kind = self._next_kind(str(last_closed_row[0]) if last_closed_row else None)
            hypothesis = f"Advance organism through {next_kind} objective."
            started_at = _utc_now_iso()

            conn.execute(
                """
                INSERT INTO intentions (life_number, kind, hypothesis, status, outcome, started_at, closed_at)
                VALUES (?, ?, ?, 'active', NULL, ?, NULL)
                """,
                (life_number, next_kind, hypothesis, started_at),
            )
            conn.execute(
                "UPDATE life_state SET current_intention = ?, updated_at = ? WHERE id = 1",
                (next_kind, _utc_now_iso()),
            )
            conn.commit()

        current = self.get_active_intention()
        if not current:
            raise RuntimeError("active intention missing after tick")
        return current

    def close_active(self, outcome: str) -> dict[str, object] | None:
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute(
                """
                SELECT id, life_number, kind, hypothesis, started_at
                FROM intentions
                WHERE status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            conn.execute(
                "UPDATE intentions SET status = 'closed', outcome = ?, closed_at = ? WHERE id = ?",
                (outcome, _utc_now_iso(), int(row[0])),
            )
            conn.commit()

        return {
            "id": int(row[0]),
            "life_number": int(row[1]),
            "kind": str(row[2]),
            "hypothesis": str(row[3]),
            "status": "closed",
            "outcome": outcome,
            "started_at": str(row[4]),
        }

    def get_active_intention(self) -> dict[str, object] | None:
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute(
                """
                SELECT id, life_number, kind, hypothesis, status, outcome, started_at, closed_at
                FROM intentions
                WHERE status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        return self._serialize(row)

    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        with sqlite3.connect(self.database_path) as conn:
            rows = conn.execute(
                """
                SELECT id, life_number, kind, hypothesis, status, outcome, started_at, closed_at
                FROM intentions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._serialize(row) for row in rows]

    def _next_kind(self, previous: str | None) -> str:
        if previous not in INTENTION_SEQUENCE:
            return INTENTION_SEQUENCE[0]
        idx = INTENTION_SEQUENCE.index(previous)
        return INTENTION_SEQUENCE[(idx + 1) % len(INTENTION_SEQUENCE)]

    def _serialize(self, row: tuple) -> dict[str, object]:
        return {
            "id": int(row[0]),
            "life_number": int(row[1]),
            "kind": str(row[2]),
            "hypothesis": str(row[3]),
            "status": str(row[4]),
            "outcome": str(row[5]) if row[5] is not None else None,
            "started_at": str(row[6]),
            "closed_at": str(row[7]) if row[7] is not None else None,
        }
