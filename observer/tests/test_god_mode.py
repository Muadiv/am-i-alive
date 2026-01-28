# TASK-004: God mode tests
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks


@pytest.mark.asyncio
async def test_kill_endpoint_with_custom_cause(main_module, monkeypatch, test_db):
    """Kill endpoint should accept custom death cause."""
    # Mock state as alive
    monkeypatch.setattr(test_db, "get_current_state", AsyncMock(return_value={"is_alive": True}))
    monkeypatch.setattr(main_module, "execute_death", AsyncMock())

    request_data = {"cause": "code_restart"}

    class FakeRequest:
        client = type("Client", (), {"host": "192.168.0.10"})()

        async def json(self):
            return request_data

    bg_tasks = BackgroundTasks()
    response = await main_module.kill_ai(FakeRequest(), bg_tasks)

    assert response["success"] is True
    assert response["cause"] == "code_restart"


@pytest.mark.asyncio
async def test_death_recorded_with_custom_reason(test_db):
    """Death should be recorded with custom cause in database."""
    await test_db.record_death(cause="testing_respawn", summary="Test death", vote_counts=None, final_vote_result=None)

    import sqlite3

    import aiosqlite

    async with aiosqlite.connect(
        test_db.DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    ) as conn:
        cursor = await conn.execute("SELECT cause FROM deaths ORDER BY death_time DESC LIMIT 1")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "testing_respawn"


@pytest.mark.asyncio
async def test_custom_cause_appears_in_history(test_db):
    """Custom death causes should appear in life history."""
    await test_db.record_birth(1, "basic_facts", "test")
    await test_db.record_death("code_deployment", "Deployed new code", None, None)

    history = await test_db.get_life_history()
    assert len(history) > 0
    latest = history[0]
    assert latest["cause"] == "code_deployment"
