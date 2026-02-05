from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
