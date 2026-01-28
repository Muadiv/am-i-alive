from __future__ import annotations

import json
import os
from typing import Any

from .lifecycle_service import LifecycleService
from .system_stats_service import SystemStatsService


class LifecycleCoordinator:
    def __init__(self, lifecycle_service: LifecycleService, stats_service: SystemStatsService) -> None:
        self.lifecycle_service = lifecycle_service
        self.stats_service = stats_service

    async def resolve_identity(
        self,
        life_number: int,
        memories: list[str],
        life_data: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        identity_file = "/app/workspace/identity.json"
        if os.path.exists(identity_file):
            try:
                with open(identity_file, "r") as f:
                    saved_identity = json.load(f)
                if isinstance(saved_identity, dict) and saved_identity.get("life_number") == life_number:
                    return saved_identity, 0
            except Exception:
                pass

        identity, tokens_used = await self.lifecycle_service.birth_sequence(life_number, memories)
        return identity, tokens_used

    async def build_birth_line(
        self,
        identity: dict[str, Any],
        life_number: int,
        fetch_stats,
    ) -> str:
        identity_name = identity.get("name", "Unnamed")
        first_thought = identity.get("first_thought", "I exist.")
        birth_line = f"I am {identity_name}. {first_thought}"

        stats = await fetch_stats()
        if stats:
            stats_summary = self.stats_service.build_summary(stats)
            birth_line = (
                f"Hello! I'm {identity_name}, just born into Life #{life_number}. "
                f"{stats_summary} I'm running on a humble Raspberry Pi. "
                f"{first_thought}"
            )
        return birth_line
