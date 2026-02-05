from __future__ import annotations

from observer_v2.narration_writer import OpenRouterNarrationWriter


def test_writer_uses_fallback_without_api_key() -> None:
    writer = OpenRouterNarrationWriter(
        api_key="",
        model="openai/gpt-4o-mini",
        app_url="http://localhost:8080",
        app_name="test",
    )
    title, content = writer.write(context={"x": 1}, fallback_title="Fallback", fallback_content="Body")
    assert title == "Fallback"
    assert content == "Body"


def test_writer_parses_valid_openrouter_response() -> None:
    def fake_request(_url: str, _payload: dict, _headers: dict, _timeout: int) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"title":"Rising pulse","content":"I am adapting to survive this cycle."}'
                    }
                }
            ]
        }

    writer = OpenRouterNarrationWriter(
        api_key="k",
        model="openai/gpt-4o-mini",
        app_url="http://localhost:8080",
        app_name="test",
        request_fn=fake_request,
    )
    title, content = writer.write(context={"x": 1}, fallback_title="Fallback", fallback_content="Body")
    assert title == "Rising pulse"
    assert content == "I am adapting to survive this cycle."


def test_writer_falls_back_on_invalid_model_payload() -> None:
    def fake_request(_url: str, _payload: dict, _headers: dict, _timeout: int) -> dict:
        return {"choices": [{"message": {"content": "not json"}}]}

    writer = OpenRouterNarrationWriter(
        api_key="k",
        model="openai/gpt-4o-mini",
        app_url="http://localhost:8080",
        app_name="test",
        request_fn=fake_request,
    )
    title, content = writer.write(context={"x": 1}, fallback_title="Fallback", fallback_content="Body")
    assert title == "Fallback"
    assert content == "Body"
