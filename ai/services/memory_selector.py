from __future__ import annotations

import random
from typing import Any


class MemorySelector:
    def select(
        self,
        memories: list[str],
        state_info: str,
        credit_status: dict[str, Any],
        sys_stats: dict[str, Any],
        max_items: int = 3,
    ) -> list[str]:
        if not memories:
            return []

        scores: list[tuple[int, str]] = []
        state_text = state_info.lower() if state_info else ""
        temp = str(sys_stats.get("cpu_temp", ""))
        disk = str(sys_stats.get("disk_usage", ""))
        budget = float(credit_status.get("balance", 0.0))

        for memory in memories:
            score = 0
            text = memory.lower()
            if "die" in state_text or "dead" in state_text:
                score += 2 if "die" in text or "death" in text else 0
            if "live" in state_text:
                score += 2 if "live" in text or "alive" in text else 0
            if budget < 1.0:
                score += 2 if "budget" in text or "money" in text else 0
            if temp and "temp" in text:
                score += 1
            if disk and "disk" in text:
                score += 1
            scores.append((score, memory))

        scores.sort(key=lambda item: item[0], reverse=True)
        top = [mem for score, mem in scores if score > 0][: max_items - 1]

        remaining = [mem for mem in memories if mem not in top]
        if remaining:
            top.append(random.choice(remaining))

        random.shuffle(top)
        return top[:max_items]
