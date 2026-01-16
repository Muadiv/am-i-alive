# TASK-004: Message tests
import importlib
import json
import os
import sys
import types
from unittest.mock import AsyncMock

import pytest


ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)


@pytest.mark.asyncio
async def test_read_messages_action_works(test_db):
    """read_messages should return unread messages."""
    await test_db.submit_visitor_message("Test User", "Hello AI!", "test_hash_123")

    messages = await test_db.get_unread_messages()
    assert len(messages) >= 1
    assert any(m["message"] == "Hello AI!" for m in messages)


@pytest.mark.asyncio
async def test_messages_marked_as_read(test_db):
    """Messages should be marked as read after reading."""
    result = await test_db.submit_visitor_message("User", "Test message", "hash_456")
    message_id = result.get("id")

    await test_db.mark_messages_read([message_id])

    unread = await test_db.get_unread_messages()
    assert not any(m["id"] == message_id for m in unread)


@pytest.mark.asyncio
async def test_message_count_endpoint(main_module, test_db, monkeypatch):
    """Message count endpoint should return correct count."""
    monkeypatch.setattr(main_module.db, "get_unread_message_count", AsyncMock(return_value=3))

    response = await main_module.get_message_count()
    assert response["count"] == 3


@pytest.mark.asyncio
async def test_oracle_message_delivery_marked(test_db):
    """Oracle messages should be marked delivered after ack."""
    result = await test_db.submit_oracle_message("Hello", "oracle")
    message_id = result.get("id")

    await test_db.mark_oracle_message_delivered(message_id)

    messages = await test_db.get_all_messages(limit=10)
    oracle_messages = messages.get("oracle_messages", [])
    stored = next(msg for msg in oracle_messages if msg["id"] == message_id)

    assert stored["delivered"] == 1


@pytest.mark.asyncio
async def test_oracle_message_sends_message_id(main_module, test_db, monkeypatch):
    """Oracle endpoint should forward message_id to the AI."""
    class FakeResponse:
        def json(self):
            return {"status": "received"}

    class FakeAsyncClient:
        def __init__(self):
            self.payloads = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, _url, json=None, timeout=None):
            self.payloads.append(json or {})
            return FakeResponse()

    fake_client = FakeAsyncClient()
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda: fake_client)

    class FakeRequest:
        client = type("Client", (), {"host": "127.0.0.1"})()
        headers = {}

        async def json(self):
            return {"message": "Hello AI", "type": "oracle"}

    await main_module.oracle_message(FakeRequest())

    oracle_messages = await test_db.get_all_messages(limit=10)
    message_id = oracle_messages["oracle_messages"][0]["id"]

    assert fake_client.payloads
    assert fake_client.payloads[0]["message_id"] == message_id


def test_vault_capture_writes_secret(tmp_path, monkeypatch):
    """Vault capture should persist detected secrets."""
    vault_path = tmp_path / "vault"
    log_path = tmp_path / "logs"
    monkeypatch.setenv("VAULT_PATH", str(vault_path))
    monkeypatch.setenv("LOG_PATH", str(log_path))

    sys.modules["mitmproxy"] = types.ModuleType("mitmproxy")
    sys.modules["mitmproxy"].http = types.SimpleNamespace(HTTPFlow=object)

    from proxy import intercept

    importlib.reload(intercept)

    intercept.check_for_secrets(
        "password=testing123",
        {"url": "http://example.com", "method": "POST", "type": "request"}
    )

    vault_file = vault_path / "secrets.json"
    assert vault_file.exists()

    data = json.loads(vault_file.read_text())
    assert data[0]["type"] == "password_form"
