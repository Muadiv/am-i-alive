from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LifecycleData:
    life_number: int
    bootstrap_mode: str
    model: str
    previous_death_cause: str | None
    previous_life: dict[str, Any] | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LifecycleData":
        life_number_val = payload.get("life_number")
        if life_number_val is None:
            raise ValueError("birth_sequence requires life_number from Observer")
        try:
            life_number = int(life_number_val)
        except (TypeError, ValueError) as exc:
            raise ValueError("birth_sequence requires numeric life_number from Observer") from exc

        bootstrap_mode_val = payload.get("bootstrap_mode") or ""
        model_val = payload.get("model") or "unknown"

        previous_death_cause = payload.get("previous_death_cause")
        previous_life = payload.get("previous_life")

        return cls(
            life_number=life_number,
            bootstrap_mode=str(bootstrap_mode_val),
            model=str(model_val),
            previous_death_cause=str(previous_death_cause) if previous_death_cause else None,
            previous_life=previous_life if isinstance(previous_life, dict) else None,
        )
