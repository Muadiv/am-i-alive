import pytest

from ai.services.prompt_service import PromptService


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
    service = PromptService(client, observer_url)

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
    service = PromptService(client, observer_url)

    prompt = await service.build_prompt(
        identity={"name": "Test", "pronoun": "it"},
        state_info="State",
        credit_status={"balance": 1.0, "budget": 5.0, "status": "ok"},
        current_model={"name": "Model", "intelligence": 5},
        sys_stats={},
    )

    assert "MANDATORY" in prompt
