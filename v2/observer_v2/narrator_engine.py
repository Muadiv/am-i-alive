from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class NarratorEngine:
    minimum_interval_seconds: int = 180

    def should_emit(self, last_created_at: str | None, now: datetime | None = None) -> bool:
        if not last_created_at:
            return True
        current = now or _utc_now()
        last = _parse_iso(last_created_at)
        elapsed = (current - last).total_seconds()
        return elapsed >= self.minimum_interval_seconds

    def build_narration(
        self,
        life_state: dict[str, object],
        vote_round: dict[str, object] | None,
        active_intention: dict[str, object] | None,
        donations_count: int,
    ) -> tuple[str, str]:
        life_number = int(life_state.get("life_number", 0))
        state = str(life_state.get("state", "unknown"))
        is_alive = bool(life_state.get("is_alive", False))
        intention = "observe" if not active_intention else str(active_intention.get("kind", "observe"))

        if not is_alive:
            return (
                "Silence phase",
                f"Life {life_number} is currently {state}. Rebirth conditions are being prepared.",
            )

        live_votes = int(vote_round.get("live", 0)) if vote_round else 0
        die_votes = int(vote_round.get("die", 0)) if vote_round else 0
        pressure = "stable"
        if die_votes > live_votes:
            pressure = "threatened"
        if donations_count > 0:
            pressure = "supported"

        title = "Pulse update"
        if pressure == "threatened":
            title = "Survival pressure rising"
        elif pressure == "supported":
            title = "Support is extending runway"

        content = (
            f"Life {life_number} remains {state}. "
            f"Active intention: {intention}. "
            f"Vote pressure live/die: {live_votes}/{die_votes}. "
            f"Observed support events: {donations_count}."
        )
        return title, content
