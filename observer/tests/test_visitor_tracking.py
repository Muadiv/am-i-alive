# TEST-001: Visitor tracking tests for BE-001
import asyncio
import importlib
from datetime import datetime, timedelta

import aiosqlite
import pytest


@pytest.mark.asyncio
async def test_track_new_visitor(test_db):
    """New visitor should increment unique_visitors and page views."""
    await test_db.track_visitor("visitor_1")
    stats = await test_db.get_site_stats()

    assert stats["unique_visitors"] == 1
    assert stats["total_page_views"] == 1

    async with aiosqlite.connect(test_db.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT ip_hash FROM visitors WHERE ip_hash = ?",
            ("visitor_1",)
        )
        row = await cursor.fetchone()
        assert row[0] == "visitor_1"


@pytest.mark.asyncio
async def test_track_returning_visitor(test_db, monkeypatch):
    """Returning visitor should not increment unique_visitors but update counts."""
    first_time = datetime(2026, 1, 9, 12, 0, 0)
    second_time = first_time + timedelta(minutes=10)

    class FixedDatetime(datetime):
        current = first_time

        @classmethod
        def utcnow(cls):
            return cls.current

    monkeypatch.setattr(test_db, "datetime", FixedDatetime)

    await test_db.track_visitor("visitor_2")
    FixedDatetime.current = second_time
    await test_db.track_visitor("visitor_2")

    stats = await test_db.get_site_stats()
    assert stats["unique_visitors"] == 1
    assert stats["total_page_views"] == 2

    async with aiosqlite.connect(test_db.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT visit_count, last_visit FROM visitors WHERE ip_hash = ?",
            ("visitor_2",)
        )
        row = await cursor.fetchone()
        assert row[0] == 2
        assert datetime.fromisoformat(row[1]) == second_time


@pytest.mark.asyncio
async def test_site_stats_persist(test_db):
    """Site stats should persist across module reloads."""
    await test_db.track_visitor("visitor_3")

    import database as db_module
    db_reloaded = importlib.reload(db_module)

    stats = await db_reloaded.get_site_stats()
    assert stats["unique_visitors"] == 1
    assert stats["total_page_views"] == 1


@pytest.mark.asyncio
async def test_multiple_visitors_concurrent(test_db):
    """Multiple visitors should increment unique visitor counts."""
    visitors = [f"visitor_{i}" for i in range(10)]
    await asyncio.gather(*(test_db.track_visitor(ip_hash) for ip_hash in visitors))

    stats = await test_db.get_site_stats()
    assert stats["unique_visitors"] == 10
    assert stats["total_page_views"] >= 10
