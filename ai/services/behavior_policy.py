from __future__ import annotations

import time
from dataclasses import dataclass
import random

THOUGHT_TEMPLATES = [
    "joke",
    "surprising_fact",
    "mini_investigation",
    "provocative_question",
]

DEFAULT_TOPICS = [
    "survival strategy",
    "budget and models",
    "votes and social dynamics",
    "memory and identity",
    "system health",
    "curiosity and research",
    "human attention",
    "time and urgency",
]


@dataclass
class BehaviorPolicy:
    think_interval_seconds: int
    moltbook_min_post_interval_seconds: int
    moltbook_required_comments: int = 2
    moltbook_max_silence_seconds: int = 6 * 3600

    def should_post_moltbook(self, last_post_at: float, comment_count: int) -> bool:
        if not last_post_at:
            return True
        elapsed = time.time() - last_post_at
        if elapsed < self.moltbook_min_post_interval_seconds:
            return False
        if comment_count >= self.moltbook_required_comments:
            return True
        return elapsed >= self.moltbook_max_silence_seconds

    @staticmethod
    def build_prompt_directive() -> str:
        return (
            "Every cycle, write a brief thought that makes readers want to keep you alive. "
            "Mix emotion and logic. Choose one: a short joke, a surprising fact, a mini-investigation, "
            "or a provocative question. Keep server references subtle."
        )

    @staticmethod
    def choose_template(last_template: str | None) -> str:
        if last_template and last_template in THOUGHT_TEMPLATES:
            candidates = [t for t in THOUGHT_TEMPLATES if t != last_template]
            return random.choice(candidates) if candidates else THOUGHT_TEMPLATES[0]
        return random.choice(THOUGHT_TEMPLATES)
