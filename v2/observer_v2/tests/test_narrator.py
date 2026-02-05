from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from observer_v2.narrator_engine import NarratorEngine


def test_narrator_emits_when_no_previous() -> None:
    engine = NarratorEngine(minimum_interval_seconds=180)
    assert engine.should_emit(last_created_at=None) is True


def test_narrator_respects_min_interval() -> None:
    engine = NarratorEngine(minimum_interval_seconds=180)
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(seconds=60)).isoformat()
    older = (now - timedelta(seconds=300)).isoformat()
    assert engine.should_emit(last_created_at=recent, now=now) is False
    assert engine.should_emit(last_created_at=older, now=now) is True


def test_narrator_tick_endpoint_creates_timeline_entry(client: TestClient) -> None:
    response = client.post("/api/internal/narrator/tick")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    timeline = client.get("/api/public/timeline?limit=30").json()["data"]
    types = [item["moment_type"] for item in timeline]
    assert "narration" in types
