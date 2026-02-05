from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sqlite3

from .voting import ROUND_DURATION_HOURS, VoteRound, adjudicate_round


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass
class VoteRoundService:
    database_path: str

    def cast_vote(self, voter_fingerprint: str, vote: str, reason: str | None = None) -> dict[str, object]:
        if vote not in {"live", "die"}:
            raise ValueError("vote must be 'live' or 'die'")
        if not voter_fingerprint:
            raise ValueError("voter_fingerprint is required")

        with sqlite3.connect(self.database_path) as conn:
            round_row = self._get_open_round_row(conn)
            if not round_row:
                raise RuntimeError("No open vote round")

            try:
                conn.execute(
                    """
                    INSERT INTO votes (round_id, voter_fingerprint, vote, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (int(round_row[0]), voter_fingerprint, vote, reason or "", datetime.now(timezone.utc).isoformat()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("already voted in current round") from exc

            live_count, die_count = self._count_round_votes(conn, int(round_row[0]))
            conn.execute(
                "UPDATE vote_rounds SET live_count = ?, die_count = ? WHERE id = ?",
                (live_count, die_count, int(round_row[0])),
            )
            conn.commit()

        return {
            "round_id": int(round_row[0]),
            "live": live_count,
            "die": die_count,
            "total": live_count + die_count,
        }

    def close_round_if_due(self, now: datetime | None = None) -> dict[str, object]:
        now_dt = now or datetime.now(timezone.utc)
        with sqlite3.connect(self.database_path) as conn:
            round_row = self._get_open_round_row(conn)
            if not round_row:
                return {"closed": False, "reason": "no_open_round"}

            ends_at = _parse_utc(str(round_row[2]))
            if now_dt < ends_at:
                return {"closed": False, "reason": "not_due"}

            vote_round = VoteRound(
                starts_at=_parse_utc(str(round_row[1])),
                ends_at=ends_at,
                live_count=int(round_row[3]),
                die_count=int(round_row[4]),
                status="open",
            )
            verdict = adjudicate_round(vote_round)

            conn.execute("UPDATE vote_rounds SET status = 'closed' WHERE id = ?", (int(round_row[0]),))
            conn.commit()

        return {
            "closed": True,
            "verdict": verdict,
            "live": vote_round.live_count,
            "die": vote_round.die_count,
            "total": vote_round.live_count + vote_round.die_count,
        }

    def open_new_round(self, start_time: datetime | None = None) -> None:
        start = start_time or datetime.now(timezone.utc)
        end = start + timedelta(hours=ROUND_DURATION_HOURS)
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO vote_rounds (starts_at, ends_at, live_count, die_count, status)
                VALUES (?, ?, 0, 0, 'open')
                """,
                (start.isoformat(), end.isoformat()),
            )
            conn.commit()

    def reset_rounds_for_new_life(self, start_time: datetime | None = None) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute("UPDATE vote_rounds SET status = 'closed' WHERE status = 'open'")
            conn.commit()
        self.open_new_round(start_time=start_time)

    def _get_open_round_row(self, conn: sqlite3.Connection) -> tuple | None:
        return conn.execute(
            """
            SELECT id, starts_at, ends_at, live_count, die_count
            FROM vote_rounds
            WHERE status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    def _count_round_votes(self, conn: sqlite3.Connection, round_id: int) -> tuple[int, int]:
        row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN vote = 'live' THEN 1 ELSE 0 END),
                SUM(CASE WHEN vote = 'die' THEN 1 ELSE 0 END)
            FROM votes
            WHERE round_id = ?
            """,
            (round_id,),
        ).fetchone()
        live_count = int(row[0] or 0)
        die_count = int(row[1] or 0)
        return live_count, die_count
