from __future__ import annotations

import pytest

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
