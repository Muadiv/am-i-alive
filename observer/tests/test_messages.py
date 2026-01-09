# TASK-004: Message tests
from unittest.mock import AsyncMock

import pytest


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
