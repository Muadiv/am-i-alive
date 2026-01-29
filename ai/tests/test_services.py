from __future__ import annotations

from typing import Any, cast

import httpx
import pytest

from ai.core.action_processor import ActionProcessor
from ai.services.action_handler import ActionHandler
from ai.services.chat_service import ChatService
from ai.services.echo_service import EchoService
from ai.services.interfaces import ObserverClientProtocol
from ai.services.observer_client import ObserverClient
from ai.services.reporting_service import ReportingService
from ai.services.weather_service import WeatherService


class DummyHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.responses: dict[str, Any] = {}

    async def post(self, url: str, **kwargs: Any):
        self.calls.append(("post", url, kwargs))
        return self.responses.get(url, DummyResponse(200, {}))

    async def get(self, url: str, **kwargs: Any):
        self.calls.append(("get", url, kwargs))
        return self.responses.get(url, DummyResponse(200, {}))


class DummyResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = ""

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("error")


@pytest.mark.asyncio
async def test_observer_client_fetch_system_stats():
    client = DummyHttpClient()
    client.responses["http://observer/api/system/stats"] = DummyResponse(200, {"cpu": 1})
    service = ObserverClient(cast(httpx.AsyncClient, client), "http://observer")

    stats = await service.fetch_system_stats()

    assert stats == {"cpu": 1}


def test_chat_service_extracts_usage():
    service = ChatService(cast(httpx.AsyncClient, DummyHttpClient()), "http://openrouter", {})
    data = {"choices": [{"message": {"content": "hello"}}], "usage": {"prompt_tokens": 2, "completion_tokens": 3}}

    response, usage = service.extract_response(data)
    input_tokens, output_tokens = service.extract_usage(usage)

    assert response == "hello"
    assert input_tokens == 2
    assert output_tokens == 3


def test_echo_service_uses_chat_service():
    dummy_chat = ChatService(cast(httpx.AsyncClient, DummyHttpClient()), "http://openrouter", {})
    service = EchoService(dummy_chat, "http://openrouter", {})

    data = {"choices": [{"message": {"content": "echo"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    response, usage = dummy_chat.extract_response(data)

    assert service.api_url == "http://openrouter"
    assert response == "echo"
    assert usage["prompt_tokens"] == 1


def test_reporting_service_sanitizes_action_json():
    processor = ActionProcessor(action_executor=None, send_message=None, report_thought=None)
    service = ReportingService(processor)

    cleaned = service.sanitize_thought('{"action":"write_blog_post","params":{}}')

    assert cleaned == ""


@pytest.mark.asyncio
async def test_weather_service_builds_report():
    client = DummyHttpClient()
    client.responses["https://api.open-meteo.com/v1/forecast"] = DummyResponse(
        200,
        {
            "current": {
                "temperature_2m": -8,
                "apparent_temperature": -12,
                "wind_speed_10m": 12.5,
                "weather_code": 71,
                "time": "2026-01-29T12:00",
            }
        },
    )
    service = WeatherService(cast(httpx.AsyncClient, client), 50.0755, 14.4378)

    data = await service.fetch_weather()
    report = service.build_report(data)

    assert "Temperature" in report
    assert "Snow" in report or "snow" in report


@pytest.mark.asyncio
async def test_action_handler_builds_blog_title():
    async def report_activity(*_args, **_kwargs):
        return None

    async def fetch_system_stats():
        return {}

    handler = ActionHandler(
        http_client=cast(httpx.AsyncClient, DummyHttpClient()),
        observer_url="http://observer",
        observer_client=DummyObserverClient(),
        get_identity=lambda: {"name": "Test"},
        get_life_number=lambda: 1,
        report_activity=report_activity,
        fetch_system_stats=fetch_system_stats,
    )

    title = ""
    content = "# Hello\nThis is content that should be long enough to pass validation." + "x" * 120

    result = await handler.write_blog_post(title, content, [])

    assert "Blog post" in result


class DummyObserverClient(ObserverClientProtocol):
    async def report_thought(self, payload: dict[str, Any]) -> None:
        return None

    async def report_activity(self, payload: dict[str, Any]) -> None:
        return None

    async def send_heartbeat(self, payload: dict[str, Any]) -> None:
        return None

    async def notify_birth(self, payload: dict[str, Any]) -> httpx.Response:
        raise RuntimeError("not used")

    async def fetch_system_stats(self) -> dict[str, Any]:
        return {}

    async def fetch_messages_count(self) -> int | None:
        return 0

    async def fetch_blog_post_count(self) -> int | None:
        return 0

    async def fetch_votes(self) -> dict[str, Any]:
        return {}

    async def fetch_messages(self) -> dict[str, Any]:
        return {"messages": []}

    async def mark_messages_read(self, message_ids: list[int]) -> None:
        return None

    async def fetch_state(self) -> dict[str, Any]:
        return {}
