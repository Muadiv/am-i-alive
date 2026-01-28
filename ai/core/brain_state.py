from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrainState:
    identity: dict[str, Any] | None
    model_name: str
    balance: float
    life_number: int | None
    bootstrap_mode: str | None
