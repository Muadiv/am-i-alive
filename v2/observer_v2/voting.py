from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

MIN_VOTES_FOR_DEATH = 3
ROUND_DURATION_HOURS = 24


@dataclass
class VoteRound:
    starts_at: datetime
    ends_at: datetime
    live_count: int = 0
    die_count: int = 0
    status: str = "open"


def start_vote_round(start_time: datetime | None = None) -> VoteRound:
    start = start_time or datetime.now(timezone.utc)
    end = start + timedelta(hours=ROUND_DURATION_HOURS)
    return VoteRound(starts_at=start, ends_at=end)


def total_votes(vote_round: VoteRound) -> int:
    return vote_round.live_count + vote_round.die_count


def adjudicate_round(vote_round: VoteRound) -> str:
    total = total_votes(vote_round)
    if total >= MIN_VOTES_FOR_DEATH and vote_round.die_count > vote_round.live_count:
        return "die"
    return "live"
