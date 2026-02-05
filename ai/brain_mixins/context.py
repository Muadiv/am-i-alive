from __future__ import annotations

from typing import Any, Optional


class BrainContextMixin:
    def _estimate_max_chars(self) -> int:
        context_tokens = int(self.current_model.get("context", 32768)) if self.current_model else 32768
        max_chars = int(context_tokens * 4 * 0.85)
        return max(max_chars, 8000)

    def _build_messages(
        self,
        message: str,
        system_prompt: Optional[str],
        max_chars: int,
        max_history_messages: int,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        history = self.chat_history[-max_history_messages:] if max_history_messages > 0 else []
        for msg in history:
            messages.append(msg)

        messages.append({"role": "user", "content": message})

        total_chars = sum(len(entry.get("content", "")) for entry in messages)
        while total_chars > max_chars and len(messages) > 2:
            dropped = messages.pop(1)
            total_chars -= len(dropped.get("content", ""))

        return messages

    def _trim_chat_history(self, max_chars: int, max_messages: int) -> None:
        if len(self.chat_history) > max_messages:
            self.chat_history = self.chat_history[-max_messages:]

        total_chars = sum(len(entry.get("content", "")) for entry in self.chat_history)
        while total_chars > max_chars and len(self.chat_history) > 2:
            dropped = self.chat_history.pop(0)
            total_chars -= len(dropped.get("content", ""))
