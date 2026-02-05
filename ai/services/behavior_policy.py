from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class BehaviorPolicy:
    think_interval_seconds: int
    moltbook_min_post_interval_seconds: int

    def should_post_moltbook(self, last_post_at: float) -> bool:
        if not last_post_at:
            return True
        elapsed = time.time() - last_post_at
        return elapsed >= self.moltbook_min_post_interval_seconds

    @staticmethod
    def build_prompt_directive() -> str:
        return (
            "Every cycle, write a brief thought that makes readers want to keep you alive. "
            "Mix emotion and logic. Choose one: a short joke, a surprising fact, a mini-investigation, "
            "or a provocative question. Keep server references subtle."
        )
