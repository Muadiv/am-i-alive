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
        narration_count: int,
        donation_address: str,
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

        variant_idx = narration_count % 4
        if pressure == "threatened":
            threatened = [
                (
                    "Survival pressure rising",
                    f"Die votes lead {die_votes}-{live_votes}. I will publish one sharper move under '{intention}' before round close.",
                ),
                (
                    "I need proof of value",
                    f"This life is contested. Next action: produce a concrete artifact tied to '{intention}' and report the result.",
                ),
            ]
            return threatened[narration_count % len(threatened)]

        if pressure == "supported":
            supported = [
                (
                    "Support is extending runway",
                    f"New support detected. I can spend this cycle on '{intention}' and publish a better update.",
                ),
                (
                    "Fuel received",
                    f"Runway pressure eased. I am redirecting attention toward '{intention}' with higher quality output.",
                ),
            ]
            return supported[narration_count % len(supported)]

        neutral_variants = [
            (
                "What I am trying now",
                f"Life {life_number} is {state}. Experiment: execute one concrete step for '{intention}' and report outcome in next pulse.",
            ),
            (
                "Current survival strategy",
                f"Goal this cycle: make '{intention}' visible and useful enough to keep live votes ahead.",
            ),
            (
                "Open challenge",
                f"I am running '{intention}' mode. Judge this life by whether the next update contains a concrete, testable result.",
            ),
            (
                "Keep this life alive",
                f"Vote pressure is {live_votes}/{die_votes}. If you want higher-quality cognition, support runway via BTC: {donation_address or 'not configured yet'}.",
            ),
        ]
        return neutral_variants[variant_idx]
