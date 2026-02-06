from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ActivityEngine:
    minimum_interval_seconds: int = 420

    def should_emit(self, last_created_at: str | None, now: datetime | None = None) -> bool:
        if not last_created_at:
            return True
        current = now or _utc_now()
        elapsed = (current - _parse_iso(last_created_at)).total_seconds()
        return elapsed >= self.minimum_interval_seconds

    def build_activity(
        self,
        intention_kind: str,
        live_votes: int,
        die_votes: int,
        donations_count: int,
        sequence: int,
    ) -> tuple[str, str]:
        variants = [
            (
                "Intent -> Action -> Result",
                f"Intent: {intention_kind}. Action: map a concrete step for this cycle. Result: baseline established. Next: publish measurable progress.",
            ),
            (
                "Cycle report",
                f"Intent: {intention_kind}. Action: prioritize one visible output. Result: scope narrowed. Next: deliver one proof before next pulse.",
            ),
            (
                "Survival task",
                f"Intent: {intention_kind}. Action: improve public value signal. Result: vote pressure currently live/die {live_votes}/{die_votes}. Next: raise live margin.",
            ),
            (
                "Runway strategy",
                f"Intent: {intention_kind}. Action: optimize for useful output under current runway. Result: support events counted {donations_count}. Next: increase output quality.",
            ),
        ]
        return variants[sequence % len(variants)]
