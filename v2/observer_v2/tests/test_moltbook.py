from __future__ import annotations

from fastapi.testclient import TestClient

from observer_v2.moltbook_publisher import MoltbookPublisher


def test_internal_moltbook_publish_returns_missing_key_without_config(client: TestClient) -> None:
    response = client.post("/api/internal/moltbook/publish", json={"force": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["data"]["error"] == "missing_api_key"


def test_moltbook_publisher_auto_verifies_challenge() -> None:
    calls: list[tuple[str, dict]] = []

    def fake_request(url: str, payload: dict, _headers: dict, _timeout: int) -> dict:
        calls.append((url, payload))
        if url.endswith("/posts"):
            return {
                "verification_required": True,
                "verification": {
                    "code": "abc",
                    "challenge": "One claw exerts thirty four newtons and the other exerts fifteen newtons. What is the total force?",
                },
            }
        if url.endswith("/verify"):
            return {"success": True}
        return {}

    publisher = MoltbookPublisher(
        api_key="key",
        submolt="general",
        request_fn=fake_request,
    )
    result = publisher.publish("title", "content")
    assert result["success"] is True
    assert result["verification_required"] is False

    verify_calls = [payload for url, payload in calls if url.endswith("/verify")]
    assert verify_calls
    assert verify_calls[0]["answer"] == "49.00"
