from __future__ import annotations

from typing import Any

import httpx

from .interfaces import ChatServiceProtocol


class ChatService(ChatServiceProtocol):
    def __init__(self, http_client: httpx.AsyncClient, api_url: str, headers: dict[str, str]) -> None:
        self.http_client = http_client
        self.api_url = api_url
        self.headers = headers

    async def send(self, model_id: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        response = await self.http_client.post(
            self.api_url,
            headers=self.headers,
            json={"model": model_id, "messages": messages},
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def extract_response(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        response_text = str(data["choices"][0]["message"]["content"])
        usage = data.get("usage", {})
        return response_text, usage

    @staticmethod
    def extract_usage(usage: dict[str, Any]) -> tuple[int, int]:
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        return input_tokens, output_tokens
