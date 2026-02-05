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


def test_narrator_builds_varied_neutral_messages() -> None:
    engine = NarratorEngine(minimum_interval_seconds=180)
    life_state = {"life_number": 1, "state": "active", "is_alive": True}
    vote_round = {"live": 0, "die": 0}
    intention = {"kind": "survive"}

    t1, c1 = engine.build_narration(
        life_state=life_state,
        vote_round=vote_round,
        active_intention=intention,
        donations_count=0,
        narration_count=0,
        donation_address="",
    )
    t2, c2 = engine.build_narration(
        life_state=life_state,
        vote_round=vote_round,
        active_intention=intention,
        donations_count=0,
        narration_count=1,
        donation_address="",
    )
    assert (t1, c1) != (t2, c2)


def test_narrator_builds_threatened_message() -> None:
    engine = NarratorEngine(minimum_interval_seconds=180)
    life_state = {"life_number": 1, "state": "active", "is_alive": True}
    vote_round = {"live": 1, "die": 3}
    intention = {"kind": "survive"}
    title, content = engine.build_narration(
        life_state=life_state,
        vote_round=vote_round,
        active_intention=intention,
        donations_count=0,
        narration_count=2,
        donation_address="",
    )
    assert "survival" in title.lower() or "proof" in title.lower()
    assert "survive" in content.lower()
