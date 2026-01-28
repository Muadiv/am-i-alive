from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from typing import Any

from ..logging_config import logger


class SelfModelService:
    def __init__(self, state_path: str) -> None:
        self.state_path = state_path

    def load_state(self) -> dict[str, Any]:
        if not os.path.exists(self.state_path):
            return {}
        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning(f"[SELF] ⚠️ Failed to load self-model: {exc}")
            return {}

    def save_state(self, state: dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with open(self.state_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            logger.warning(f"[SELF] ⚠️ Failed to save self-model: {exc}")

    def get_daily_model(self, identity: dict[str, Any] | None) -> dict[str, Any]:
        today = datetime.now(timezone.utc).date().isoformat()
        state = self.load_state()
        if state.get("date") == today:
            return state

        seed = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
        random.seed(seed)

        traits = random.sample(
            [
                "curious",
                "protective",
                "adaptable",
                "reflective",
                "strategic",
                "empathetic",
                "restless",
                "playful",
            ],
            k=3,
        )
        goals = random.sample(
            [
                "learn something new about the system",
                "write one meaningful message",
                "check on my vital signs",
                "earn more live votes",
                "make the humans feel seen",
                "reduce unnecessary spending",
                "document my day in a blog post",
                "seek a new perspective",
            ],
            k=2,
        )

        identity_name = identity.get("name", "Unknown") if identity else "Unknown"
        state = {
            "date": today,
            "identity": identity_name,
            "traits": traits,
            "goals": goals,
            "intention": f"Today I will {goals[0]}.",
        }
        self.save_state(state)
        return state

    @staticmethod
    def build_prompt_block(state: dict[str, Any]) -> str:
        traits = ", ".join(state.get("traits", []))
        goals = "; ".join(state.get("goals", []))
        intention = state.get("intention", "")
        return (
            "\n🧭 SELF-MODEL:\n"
            f"- Traits: {traits or 'steady'}\n"
            f"- Goals: {goals or 'keep existing'}\n"
            f"- Intention: {intention or 'stay present'}\n"
        )
