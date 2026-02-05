from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable
from urllib import error, request


RequestFn = Callable[[str, dict[str, Any], dict[str, str], int], dict[str, Any]]


def _default_post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return parsed
    return {}


@dataclass
class OpenRouterNarrationWriter:
    api_key: str
    model: str
    app_url: str
    app_name: str
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: int = 20
    request_fn: RequestFn | None = None

    def write(self, context: dict[str, Any], fallback_title: str, fallback_content: str) -> tuple[str, str]:
        if not self.api_key.strip():
            return fallback_title, fallback_content

        post_json = self.request_fn or _default_post_json
        prompt = self._build_prompt(context=context, fallback_title=fallback_title, fallback_content=fallback_content)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 180,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.app_url,
            "X-Title": self.app_name,
        }

        try:
            parsed = post_json(f"{self.base_url}/chat/completions", payload, headers, self.timeout_seconds)
            content = self._extract_content(parsed)
            if not content:
                return fallback_title, fallback_content
            title, body = self._parse_model_payload(content)
            if not title or not body:
                return fallback_title, fallback_content
            return title, body
        except (error.URLError, json.JSONDecodeError, KeyError, ValueError, TimeoutError):
            return fallback_title, fallback_content

    def _build_prompt(self, context: dict[str, Any], fallback_title: str, fallback_content: str) -> str:
        return (
            "Write one short public organism pulse update. "
            "Return strict JSON with keys title and content. "
            "No markdown. Keep title under 8 words and content under 220 chars. "
            "Maintain alive-organism tone, not assistant tone. "
            f"\nContext JSON: {json.dumps(context, ensure_ascii=True)}"
            f"\nFallback title: {fallback_title}"
            f"\nFallback content: {fallback_content}"
        )

    def _extract_content(self, parsed: dict[str, Any]) -> str:
        choices = parsed.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message", {})
        if not isinstance(message, dict):
            return ""
        content = message.get("content", "")
        return str(content).strip()

    def _parse_model_payload(self, content: str) -> tuple[str, str]:
        if content.startswith("```"):
            content = content.strip("`\n")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return "", ""
        title = str(parsed.get("title", "")).strip()
        body = str(parsed.get("content", "")).strip()
        return title[:80], body[:320]
