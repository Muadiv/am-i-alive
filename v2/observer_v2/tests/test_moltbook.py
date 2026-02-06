from __future__ import annotations

from fastapi.testclient import TestClient

from observer_v2.moltbook_formatter import build_post_content
from observer_v2.moltbook_publisher import MoltbookPublisher
from observer_v2.moltbook_service import _extract_posts


def test_internal_moltbook_publish_returns_missing_key_without_config(client: TestClient) -> None:
    response = client.post("/api/internal/moltbook/publish", json={"force": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["data"]["error"] == "missing_api_key"


def test_internal_moltbook_replies_returns_missing_key_without_config(client: TestClient) -> None:
    response = client.post("/api/internal/moltbook/replies/tick", json={"force": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["data"]["error"] == "missing_api_key"


def test_public_moltbook_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/public/moltbook-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "publish" in payload["data"]
    assert "replies" in payload["data"]


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


def test_post_formatter_includes_url_and_btc() -> None:
    content = build_post_content(
        latest_title="Current survival strategy",
        latest_content="Goal this cycle is to produce a concrete result.",
        life_number=1,
        state="active",
        intention="survive",
        live_votes=2,
        die_votes=1,
        public_url="http://example.local",
        btc_address="bc1example",
    )
    assert "http://example.local" in content
    assert "bc1example" in content
    assert "die by bankruptcy" in content


def test_extract_posts_supports_nested_payload_shapes() -> None:
    payload = {"data": {"posts": [{"id": "1", "title": "hello"}]}}
    posts = _extract_posts(payload)
    assert len(posts) == 1
    assert posts[0]["id"] == "1"
