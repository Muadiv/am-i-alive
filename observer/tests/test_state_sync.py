# TEST-001: State sync validation tests for BE-003
from unittest.mock import AsyncMock

import pytest


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.get_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        self.get_calls += 1
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse(status_code=500)


@pytest.mark.asyncio
async def test_state_sync_skips_when_dead(main_module, monkeypatch):
    """Validator should skip when Observer says AI is dead."""
    monkeypatch.setattr(
        main_module.db,
        "get_current_state",
        AsyncMock(return_value={"is_alive": False})
    )
    fake_client = FakeAsyncClient([FakeResponse(status_code=200, json_data={"life_number": 1})])
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda: fake_client)
    force_sync = AsyncMock()
    monkeypatch.setattr(main_module, "force_ai_sync", force_sync)

    await main_module.validate_state_sync_once()

    assert fake_client.get_calls == 0
    force_sync.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_sync_no_desync(main_module, monkeypatch):
    """Validator should do nothing when life numbers match."""
    observer_state = {
        "is_alive": True,
        "life_number": 5,
        "bootstrap_mode": "basic_facts",
        "model": "sonnet"
    }
    monkeypatch.setattr(
        main_module.db,
        "get_current_state",
        AsyncMock(return_value=observer_state)
    )
    fake_client = FakeAsyncClient([FakeResponse(status_code=200, json_data={"life_number": 5})])
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda: fake_client)
    force_sync = AsyncMock()
    monkeypatch.setattr(main_module, "force_ai_sync", force_sync)

    await main_module.validate_state_sync_once()

    assert fake_client.get_calls == 1
    force_sync.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_sync_detects_desync(main_module, monkeypatch):
    """Validator should trigger force sync when life numbers differ."""
    observer_state = {
        "is_alive": True,
        "life_number": 8,
        "bootstrap_mode": "full_briefing",
        "model": "opus"
    }
    monkeypatch.setattr(
        main_module.db,
        "get_current_state",
        AsyncMock(return_value=observer_state)
    )
    fake_client = FakeAsyncClient([FakeResponse(status_code=200, json_data={"life_number": 3})])
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda: fake_client)
    force_sync = AsyncMock()
    monkeypatch.setattr(main_module, "force_ai_sync", force_sync)

    await main_module.validate_state_sync_once()

    assert fake_client.get_calls == 1
    force_sync.assert_awaited_once_with(observer_state)
