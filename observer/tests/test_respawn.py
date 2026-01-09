# TEST-001: Respawn tests for BE-002
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.post_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.post_calls += 1
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse(status_code=500)


@pytest.mark.asyncio
async def test_respawn_delay_range(main_module, monkeypatch, capsys):
    """Respawn delay should honor configured bounds and log output."""
    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(main_module.random, "randint", lambda _a, _b: 15)
    monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(main_module.db, "log_activity", AsyncMock())
    monkeypatch.setattr(
        main_module.db,
        "start_new_life",
        AsyncMock(return_value={"life_number": 2})
    )
    monkeypatch.setattr(main_module, "notify_ai_birth", AsyncMock(return_value=True))

    await main_module.schedule_respawn()
    output = capsys.readouterr().out

    assert "Respawn scheduled in 15 seconds" in output


@pytest.mark.asyncio
async def test_notify_ai_birth_success(main_module, monkeypatch):
    """Successful birth notification should return True and call once."""
    fake_client = FakeAsyncClient([FakeResponse(status_code=200)])
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda: fake_client)

    result = await main_module.notify_ai_birth({"life_number": 1})
    assert result is True
    assert fake_client.post_calls == 1


@pytest.mark.asyncio
async def test_notify_ai_birth_retry_logic(main_module, monkeypatch):
    """Notify should retry 3 times and back off on failures."""
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)
        return None

    fake_client = FakeAsyncClient([
        FakeResponse(status_code=500),
        FakeResponse(status_code=500),
        FakeResponse(status_code=500)
    ])

    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda: fake_client)
    monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)

    result = await main_module.notify_ai_birth({"life_number": 1})

    assert result is False
    assert fake_client.post_calls == 3
    assert sleep_calls == [5, 10]


@pytest.mark.asyncio
async def test_respawn_creates_new_life(test_db):
    """Respawn should increment life number and rotate bootstrap/model."""
    first = await test_db.start_new_life()
    second = await test_db.start_new_life()

    assert first["life_number"] == 1
    assert second["life_number"] == 2
    assert first["bootstrap_mode"] == "basic_facts"
    assert second["bootstrap_mode"] == "full_briefing"
    assert first["model"] == "sonnet"
    assert second["model"] == "opus"


@pytest.mark.asyncio
async def test_death_triggers_respawn(main_module, test_db, monkeypatch):
    """Manual death should schedule a respawn and log activity."""
    await test_db.start_new_life()

    async def fake_sleep(_seconds):
        return None

    fake_client = FakeAsyncClient([FakeResponse(status_code=200)])

    monkeypatch.setattr(main_module.random, "randint", lambda _a, _b: 10)
    monkeypatch.setattr(main_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda: fake_client)
    monkeypatch.setattr(main_module, "notify_ai_birth", AsyncMock(return_value=True))

    class MockRequest:
        client = type("Client", (), {"host": "192.168.0.10"})()

        async def json(self):
            return {"cause": "manual_kill"}

    background_tasks = BackgroundTasks()
    await main_module.kill_ai(MockRequest(), background_tasks)
    await background_tasks()

    activity = await test_db.get_recent_activity(20)
    actions = [item["action"] for item in activity]

    assert "respawn_scheduled" in actions
    assert "birth" in actions
