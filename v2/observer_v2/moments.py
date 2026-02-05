from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MomentsStore:
    database_path: str

    def init_schema(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS moments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    life_number INTEGER NOT NULL,
                    moment_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    visibility TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add_moment(
        self,
        life_number: int,
        moment_type: str,
        title: str,
        content: str,
        visibility: str = "public",
    ) -> dict[str, object]:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO moments (life_number, moment_type, title, content, visibility, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (life_number, moment_type, title, content, visibility, _utc_now_iso()),
            )
            row = conn.execute(
                """
                SELECT id, life_number, moment_type, title, content, visibility, created_at
                FROM moments
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            conn.commit()

        if not row:
            raise RuntimeError("moment insert failed")
        return self._serialize(row)

    def list_public(self, limit: int = 30) -> list[dict[str, object]]:
        with sqlite3.connect(self.database_path) as conn:
            rows = conn.execute(
                """
                SELECT id, life_number, moment_type, title, content, visibility, created_at
                FROM moments
                WHERE visibility = 'public'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._serialize(row) for row in rows]

    def latest(self, moment_type: str | None = None) -> dict[str, object] | None:
        with sqlite3.connect(self.database_path) as conn:
            if moment_type:
                row = conn.execute(
                    """
                    SELECT id, life_number, moment_type, title, content, visibility, created_at
                    FROM moments
                    WHERE visibility = 'public' AND moment_type = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (moment_type,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT id, life_number, moment_type, title, content, visibility, created_at
                    FROM moments
                    WHERE visibility = 'public'
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchone()
        if not row:
            return None
        return self._serialize(row)

    def _serialize(self, row: tuple) -> dict[str, object]:
        return {
            "id": int(row[0]),
            "life_number": int(row[1]),
            "moment_type": str(row[2]),
            "title": str(row[3]),
            "content": str(row[4]),
            "visibility": str(row[5]),
            "created_at": str(row[6]),
        }
