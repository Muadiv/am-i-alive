from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest

from observer_v2.storage import SqliteStorage
from observer_v2.vote_rounds import VoteRoundService


def _prepare_services(tmp_path: Path) -> tuple[SqliteStorage, VoteRoundService, str]:
    db_path = str(tmp_path / "vote_rounds.db")
    storage = SqliteStorage(db_path)
    storage.init_schema()
    storage.bootstrap_defaults()
    service = VoteRoundService(db_path)
    return storage, service, db_path


def test_vote_service_cast_and_duplicate(tmp_path: Path) -> None:
    _storage, service, _db_path = _prepare_services(tmp_path)

    first = service.cast_vote(voter_fingerprint="user-a", vote="live")
    assert first["live"] == 1
    assert first["die"] == 0

    with pytest.raises(ValueError, match="already voted"):
        service.cast_vote(voter_fingerprint="user-a", vote="die")


def test_vote_round_close_due_with_die_verdict(tmp_path: Path) -> None:
    _storage, service, db_path = _prepare_services(tmp_path)
    service.cast_vote(voter_fingerprint="user-a", vote="die")
    service.cast_vote(voter_fingerprint="user-b", vote="die")
    service.cast_vote(voter_fingerprint="user-c", vote="live")

    due_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE vote_rounds SET ends_at = ? WHERE status = 'open'", (due_time.isoformat(),))
        conn.commit()

    result = service.close_round_if_due()
    assert result["closed"] is True
    assert result["verdict"] == "die"
    assert result["total"] == 3
