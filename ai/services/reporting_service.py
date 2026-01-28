from __future__ import annotations

import re
from typing import Any

from ai.core.action_processor import ActionProcessor


class ReportingService:
    def __init__(self, action_processor: ActionProcessor) -> None:
        self.action_processor = action_processor

    def sanitize_thought(self, content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}") and '"action"' in stripped:
            action_data = self.action_processor.extract_action_data(stripped)
            if action_data:
                return ""

        cleaned_content = self.action_processor.strip_action_json(content)
        cleaned_content = re.sub(r"```[a-z]*\n", "", cleaned_content)
        cleaned_content = re.sub(r"```", "", cleaned_content)
        cleaned_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned_content)
        return cleaned_content.strip()

    @staticmethod
    def build_thought_payload(
        cleaned_content: str,
        thought_type: str,
        identity: dict[str, Any] | None,
        model_name: str,
        balance: float,
    ) -> dict[str, Any]:
        return {
            "content": cleaned_content[:2000],
            "type": thought_type,
            "tokens_used": 0,
            "identity": identity,
            "model": model_name,
            "balance": round(balance, 2),
        }

    @staticmethod
    def build_activity_payload(
        action: str,
        details: str | None,
        model_name: str,
        balance: float,
    ) -> dict[str, Any]:
        return {
            "action": action,
            "details": details,
            "model": model_name,
            "balance": round(balance, 2),
        }
