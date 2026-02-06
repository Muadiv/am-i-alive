from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass
class IntegrationStateStore:
    database_path: str

    def init_schema(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS integration_state (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_value(self, name: str) -> str | None:
        with sqlite3.connect(self.database_path) as conn:
            row = conn.execute("SELECT value FROM integration_state WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        return str(row[0])

    def set_value(self, name: str, value: str) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO integration_state (name, value)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET value = excluded.value
                """,
                (name, value),
            )
            conn.commit()
