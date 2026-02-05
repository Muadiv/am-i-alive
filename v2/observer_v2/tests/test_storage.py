from __future__ import annotations

from pathlib import Path

from observer_v2.storage import SqliteStorage


def test_storage_bootstraps_life_state(tmp_path: Path) -> None:
    db_path = tmp_path / "bootstrap.db"
    storage = SqliteStorage(str(db_path))
    storage.init_schema()
    storage.bootstrap_defaults()

    state = storage.get_life_state()
    assert state["life_number"] == 1
    assert state["is_alive"] is True
    assert state["state"] == "active"


def test_storage_vote_round_bootstrap(tmp_path: Path) -> None:
    db_path = tmp_path / "votes.db"
    storage = SqliteStorage(str(db_path))
    storage.init_schema()
    storage.bootstrap_defaults()

    vote_round = storage.get_open_vote_round()
    assert vote_round["status"] == "open"
    assert vote_round["live"] == 0
    assert vote_round["die"] == 0
