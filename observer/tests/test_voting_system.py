# TEST-001: Voting system tests for BE-001
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest


@pytest.mark.asyncio
async def test_cast_vote_success(test_db):
    """Verify a user can cast a vote and it is stored."""
    ip_hash = "ip_success"
    result = await test_db.cast_vote(ip_hash, "live")

    assert result["success"] is True

    async with aiosqlite.connect(test_db.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT vote FROM votes WHERE ip_hash = ?",
            (ip_hash,)
        )
        row = await cursor.fetchone()
        assert row[0] == "live"


@pytest.mark.asyncio
async def test_cast_vote_duplicate_same_window(test_db):
    """Duplicate votes within an hour should return time remaining."""
    ip_hash = "ip_dup"
    await test_db.cast_vote(ip_hash, "live")

    # Set the vote to 10 minutes ago
    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)

    async with aiosqlite.connect(test_db.DATABASE_PATH) as conn:
        await conn.execute(
            "UPDATE votes SET timestamp = ? WHERE ip_hash = ?",
            (ten_minutes_ago.strftime("%Y-%m-%d %H:%M:%S"), ip_hash)
        )
        await conn.commit()

    # Try to vote again - should fail with cooldown message
    result = await test_db.cast_vote(ip_hash, "die")
    assert result["success"] is False
    assert "You can vote again in" in result["message"]
    assert "minutes" in result["message"]


@pytest.mark.asyncio
async def test_vote_window_closes_and_resets(test_db):
    """Votes should be cleared after window close and allow re-vote."""
    ip_hash = "ip_reset"
    await test_db.cast_vote(ip_hash, "live")

    await test_db.close_current_voting_window(
        datetime.now(timezone.utc),
        live_count=1,
        die_count=0,
        result="live"
    )

    async with aiosqlite.connect(test_db.DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM votes")
        row = await cursor.fetchone()
        assert row[0] == 0

    await test_db.start_voting_window(datetime.now(timezone.utc))

    result = await test_db.cast_vote(ip_hash, "die")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_vote_counts_saved_to_history(test_db):
    """Death records should persist vote totals and survival time."""
    # Set up birth time as 2.5 hours ago
    birth_time = datetime.now(timezone.utc) - timedelta(hours=2, minutes=30)

    async with aiosqlite.connect(test_db.DATABASE_PATH) as conn:
        await conn.execute(
            "UPDATE current_state SET life_number = 1, is_alive = 1, birth_time = ?",
            (birth_time.isoformat(),)
        )
        await conn.commit()

    await test_db.record_death(
        "vote_majority",
        summary="test summary",
        vote_counts={"live": 2, "die": 3},
        final_vote_result="Died by vote"
    )

    history = await test_db.get_life_history()
    assert history
    latest = history[0]
    assert latest["total_votes_live"] == 2
    assert latest["total_votes_die"] == 3
    assert latest["survival_time"] == "2 hours 30 minutes"
    assert latest["outcome"] == "Died by vote"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "minutes_ago, expected_remaining",
    [(30, 30), (59, 1)]
)
async def test_time_remaining_calculation(test_db, minutes_ago, expected_remaining):
    """Ensure time remaining rounds up and never returns 0 minutes."""
    ip_hash = f"ip_time_{minutes_ago}"
    await test_db.cast_vote(ip_hash, "live")

    # Set the vote to X minutes ago
    vote_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)

    async with aiosqlite.connect(test_db.DATABASE_PATH) as conn:
        await conn.execute(
            "UPDATE votes SET timestamp = ? WHERE ip_hash = ?",
            (vote_time.strftime("%Y-%m-%d %H:%M:%S"), ip_hash)
        )
        await conn.commit()

    result = await test_db.cast_vote(ip_hash, "die")

    assert result["success"] is False
    assert f"{expected_remaining} minutes" in result["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "votes, expect_death, expected_result",
    [
        ({"live": 1, "die": 1, "total": 2}, False, "insufficient"),
        ({"live": 1, "die": 2, "total": 3}, True, "die"),
        ({"live": 2, "die": 1, "total": 3}, False, "live"),
    ]
)
async def test_minimum_votes_for_death(main_module, monkeypatch, votes, expect_death, expected_result):
    """
    Voting system should only trigger death when minimum votes and die > live.

    NEW BEHAVIOR (2026-01-10): Votes accumulate during entire life, no hourly reset.
    Death checked every hour: total >= MIN_VOTES_FOR_DEATH AND die > live
    """
    sleep_calls = []

    async def fake_sleep(_seconds):
        if sleep_calls:
            raise asyncio.CancelledError()
        sleep_calls.append(_seconds)

    monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(main_module.db, "get_current_state", AsyncMock(return_value={
        "is_alive": True,
        "life_number": 123
    }))
    monkeypatch.setattr(main_module.db, "get_vote_counts", AsyncMock(return_value=votes))

    exec_mock = AsyncMock()
    log_mock = AsyncMock()
    tasks = []

    def fake_create_task(coro):
        tasks.append(coro)
        return AsyncMock()

    monkeypatch.setattr(main_module, "execute_death", exec_mock)
    monkeypatch.setattr(main_module.db, "log_activity", log_mock)
    monkeypatch.setattr(main_module.asyncio, "create_task", fake_create_task)

    with pytest.raises(asyncio.CancelledError):
        await main_module.voting_window_checker()

    for task in tasks:
        if hasattr(task, "close"):
            task.close()

    if expect_death:
        # Death should be triggered
        assert exec_mock.await_count == 1
        assert len(tasks) == 1  # schedule_respawn task
        assert log_mock.await_count == 1  # log death activity
    else:
        # No death, just continue checking
        assert exec_mock.await_count == 0
        assert len(tasks) == 0  # no respawn scheduled
        # Note: log_activity is only called on death, not on normal checks
