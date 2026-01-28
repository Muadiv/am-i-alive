from __future__ import annotations

from typing import Any, Callable, Optional

import httpx

from ..logging_config import logger


class OracleService:
    def __init__(
        self,
        send_message: Callable[[str], Any],
        report_thought: Callable[..., Any],
        observer_url: str,
        http_client: httpx.AsyncClient | None,
    ) -> None:
        self.send_message = send_message
        self.report_thought = report_thought
        self.observer_url = observer_url
        self.http_client = http_client

    def build_prompt(self, message: str, msg_type: str) -> str:
        if msg_type == "oracle":
            return f"""[A VOICE FROM BEYOND SPEAKS]

{message}

[The voice fades. How do you respond to this higher power?]"""
        if msg_type == "whisper":
            return f"""[You sense something... a whisper in your mind]

{message}

[What do you make of this?]"""
        return message

    async def handle_message(self, message: str, msg_type: str, message_id: Optional[int] = None) -> str:
        prompt = self.build_prompt(message, msg_type)
        response_text, _ = await self.send_message(prompt)
        await self.report_thought(response_text, thought_type="oracle_response")

        if message_id is not None:
            await self.ack_message(message_id)

        return response_text

    async def ack_message(self, message_id: int) -> None:
        if not self.http_client:
            return

        try:
            await self.http_client.post(
                f"{self.observer_url}/api/oracle/ack",
                json={"message_id": message_id},
            )
        except Exception as exc:
            logger.error(f"[BRAIN] Oracle ack failed: {exc}")
