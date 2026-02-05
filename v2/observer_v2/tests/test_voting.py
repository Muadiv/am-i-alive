from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient

from observer_v2.vote_rounds import VoteRoundService
from observer_v2.voting import adjudicate_round, start_vote_round


def test_start_vote_round_sets_24h_window() -> None:
    start = datetime(2026, 2, 5, 12, 0, tzinfo=timezone.utc)
    vote_round = start_vote_round(start)
    assert vote_round.starts_at == start
    assert vote_round.ends_at == start + timedelta(hours=24)
    assert vote_round.status == "open"


def test_adjudicate_round_survives_with_insufficient_votes() -> None:
    vote_round = start_vote_round()
    vote_round.live_count = 1
    vote_round.die_count = 1
    assert adjudicate_round(vote_round) == "live"


def test_adjudicate_round_dies_with_majority_and_threshold() -> None:
    vote_round = start_vote_round()
    vote_round.live_count = 1
    vote_round.die_count = 2
    assert adjudicate_round(vote_round) == "die"


def test_adjudicate_round_lives_when_live_not_less_than_die() -> None:
    vote_round = start_vote_round()
    vote_round.live_count = 3
    vote_round.die_count = 3
    assert adjudicate_round(vote_round) == "live"


def test_public_vote_round_endpoint(client: TestClient) -> None:
    response = client.get("/api/public/vote-round")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["status"] == "open"
    assert data["live"] == 0
    assert data["die"] == 0


def test_public_vote_submission_updates_counts(client: TestClient) -> None:
    vote_response = client.post("/api/public/vote", json={"vote": "live"})
    assert vote_response.status_code == 200
    data = vote_response.json()["data"]
    assert data["live"] == 1
    assert data["die"] == 0


def test_public_vote_rejects_duplicate_voter_in_round(client: TestClient) -> None:
    first = client.post("/api/public/vote", json={"vote": "die"})
    second = client.post("/api/public/vote", json={"vote": "live"})
    assert first.status_code == 200
    assert second.status_code == 429


def test_public_vote_rejected_when_dead(client: TestClient) -> None:
    client.post("/api/internal/lifecycle/transition", json={"next_state": "dying"})
    client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "dead", "death_cause": "vote_majority"},
    )
    response = client.post("/api/public/vote", json={"vote": "live"})
    assert response.status_code == 409


def test_born_resets_round_and_allows_same_voter_again(client: TestClient) -> None:
    first_vote = client.post("/api/public/vote", json={"vote": "live"})
    assert first_vote.status_code == 200

    client.post("/api/internal/lifecycle/transition", json={"next_state": "dying"})
    client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "dead", "death_cause": "bankruptcy"},
    )
    client.post("/api/internal/lifecycle/transition", json={"next_state": "rebirth_pending"})
    client.post("/api/internal/lifecycle/transition", json={"next_state": "born"})

    second_vote = client.post("/api/public/vote", json={"vote": "die"})
    assert second_vote.status_code == 200
    counts = second_vote.json()["data"]
    assert counts["live"] == 0
    assert counts["die"] == 1


def test_close_due_round_while_dead_does_not_open_new_round(client: TestClient, database_path: Path) -> None:
    service = VoteRoundService(str(database_path))
    service.cast_vote(voter_fingerprint="user-a", vote="die")
    service.cast_vote(voter_fingerprint="user-b", vote="die")
    service.cast_vote(voter_fingerprint="user-c", vote="live")

    due_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    with sqlite3.connect(str(database_path)) as conn:
        conn.execute("UPDATE vote_rounds SET ends_at = ? WHERE status = 'open'", (due_time.isoformat(),))
        conn.commit()

    client.post("/api/internal/lifecycle/transition", json={"next_state": "dying"})
    client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "dead", "death_cause": "bankruptcy"},
    )

    close_response = client.post("/api/internal/vote-rounds/close")
    assert close_response.status_code == 200
    payload = close_response.json()["data"]
    assert payload["result"]["closed"] is True
    assert payload["result"]["action"] == "closed_while_dead"
    assert payload["open_round"] is None
