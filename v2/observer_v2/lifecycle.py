from __future__ import annotations

from dataclasses import dataclass

LIFE_STATES = {
    "born",
    "active",
    "critical",
    "dying",
    "dead",
    "rebirth_pending",
}

ALLOWED_TRANSITIONS = {
    "born": {"active"},
    "active": {"critical", "dying", "dead"},
    "critical": {"active", "dying", "dead"},
    "dying": {"dead"},
    "dead": {"rebirth_pending"},
    "rebirth_pending": {"born"},
}


@dataclass
class LifeState:
    state: str
    death_cause: str | None = None


def can_transition(current_state: str, next_state: str) -> bool:
    if current_state not in LIFE_STATES or next_state not in LIFE_STATES:
        return False
    return next_state in ALLOWED_TRANSITIONS.get(current_state, set())


def transition(life_state: LifeState, next_state: str, death_cause: str | None = None) -> LifeState:
    if not can_transition(life_state.state, next_state):
        raise ValueError(f"Invalid lifecycle transition: {life_state.state} -> {next_state}")
    if next_state == "dead" and death_cause not in {"bankruptcy", "vote_majority", None}:
        raise ValueError("Unsupported death cause")
    life_state.state = next_state
    if next_state == "dead":
        life_state.death_cause = death_cause
    return life_state
