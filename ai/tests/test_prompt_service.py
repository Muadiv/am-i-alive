from typing import cast

import httpx
import pytest

from ai.services.prompt_service import PromptService
from ai.services.system_stats_service import SystemStatsService


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class DummyHttpClient:
    def __init__(self, responses: dict[str, DummyResponse]):
        self._responses = responses

    async def get(self, url: str, timeout: float = 0):
        return self._responses.get(url, DummyResponse(500, {}))


@pytest.mark.asyncio
async def test_build_prompt_includes_unread_message_notice():
    observer_url = "http://observer"
    client = DummyHttpClient(
        {
            f"{observer_url}/api/messages/count": DummyResponse(200, {"count": 2}),
            f"{observer_url}/api/blog/posts": DummyResponse(200, {"count": 1}),
        }
    )
    service = PromptService(cast(httpx.AsyncClient, client), observer_url)

    prompt = await service.build_prompt(
        identity={"name": "Test", "pronoun": "they"},
        state_info="State",
        credit_status={"balance": 1.0, "budget": 5.0, "status": "ok"},
        current_model={"name": "Model", "intelligence": 5},
        sys_stats={},
    )

    assert "unread message" in prompt


@pytest.mark.asyncio
async def test_build_prompt_requires_blog_post_when_empty():
    observer_url = "http://observer"
    client = DummyHttpClient(
        {
            f"{observer_url}/api/messages/count": DummyResponse(200, {"count": 0}),
            f"{observer_url}/api/blog/posts": DummyResponse(200, {"count": 0}),
        }
    )
    service = PromptService(cast(httpx.AsyncClient, client), observer_url)

    prompt = await service.build_prompt(
        identity={"name": "Test", "pronoun": "it"},
        state_info="State",
        credit_status={"balance": 1.0, "budget": 5.0, "status": "ok"},
        current_model={"name": "Model", "intelligence": 5},
        sys_stats={},
    )

    assert "MANDATORY" in prompt


def test_system_stats_builds_vital_signs_report():
    client = cast(httpx.AsyncClient, object())
    service = SystemStatsService(http_client=client, observer_url="http://observer")
    report = service.build_vital_signs_report(
        {
            "cpu_temp": 60,
            "cpu_usage": 12.3,
            "ram_usage": 45.6,
            "disk_usage": 78.9,
            "uptime_seconds": 3600,
            "ram_available": "256 MB",
        }
    )

    assert "Vital signs report" in report
    assert "Temperature" in report
    assert "CPU usage" in report
    assert "RAM usage" in report
    assert "Disk usage" in report
    assert "Uptime" in report
