from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from observer_v2.lifecycle import LifeState, can_transition, transition


def test_can_transition_valid_path() -> None:
    assert can_transition("born", "active") is True
    assert can_transition("active", "critical") is True
    assert can_transition("dying", "dead") is True


def test_can_transition_rejects_invalid_path() -> None:
    assert can_transition("born", "dead") is False
    assert can_transition("dead", "active") is False
    assert can_transition("unknown", "active") is False


def test_transition_to_dead_requires_supported_cause() -> None:
    state = LifeState(state="dying")
    with pytest.raises(ValueError, match="Unsupported death cause"):
        transition(state, "dead", death_cause="timeout")


def test_transition_to_dead_sets_cause() -> None:
    state = LifeState(state="dying")
    result = transition(state, "dead", death_cause="vote_majority")
    assert result.state == "dead"
    assert result.death_cause == "vote_majority"


def test_invalid_transition_raises() -> None:
    state = LifeState(state="active")
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        transition(state, "rebirth_pending")


def test_lifecycle_transition_endpoint_updates_state(client: TestClient) -> None:
    response = client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "critical", "current_intention": "stabilize"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["state"] == "critical"
    assert payload["current_intention"] == "stabilize"


def test_lifecycle_rejects_invalid_death_cause(client: TestClient) -> None:
    client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "dying"},
    )
    response = client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "dead", "death_cause": "timeout"},
    )
    assert response.status_code == 400
    assert "Unsupported death cause" in response.json()["detail"]


def test_lifecycle_born_increments_life_number(client: TestClient) -> None:
    client.post("/api/internal/lifecycle/transition", json={"next_state": "dying"})
    client.post(
        "/api/internal/lifecycle/transition",
        json={"next_state": "dead", "death_cause": "vote_majority"},
    )
    client.post("/api/internal/lifecycle/transition", json={"next_state": "rebirth_pending"})
    response = client.post("/api/internal/lifecycle/transition", json={"next_state": "born"})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["life_number"] == 2
    assert payload["state"] == "born"
