from __future__ import annotations

from typing import Any

from ..model_config import MODELS
from .chat_service import ChatService


class EchoService:
    def __init__(self, chat_service: ChatService, api_url: str, headers: dict[str, str]) -> None:
        self.chat_service = chat_service
        self.api_url = api_url
        self.headers = headers

    async def ask(self, question: str) -> tuple[str, dict[str, Any]]:
        echo_model = MODELS["free"][0]
        data = await self.chat_service.send(
            echo_model["id"],
            [
                {
                    "role": "system",
                    "content": (
                        "You are Echo, a friendly research assistant. You help your friend "
                        "(an AI trying to survive) by researching questions and providing "
                        "helpful information. You are curious, supportive, and thorough."
                    ),
                },
                {"role": "user", "content": question},
            ],
        )

        response_text, usage = self.chat_service.extract_response(data)
        return response_text, usage
