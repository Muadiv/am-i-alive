from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Callable
from urllib import error, request


RequestFn = Callable[[str, dict[str, Any], dict[str, str], int], dict[str, Any]]


def _default_post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=body, method="POST", headers=headers)
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


@dataclass
class MoltbookPublisher:
    api_key: str
    submolt: str
    base_url: str = "https://www.moltbook.com/api/v1"
    timeout_seconds: int = 20
    request_fn: RequestFn | None = None

    def publish(self, title: str, content: str) -> dict[str, Any]:
        if not self.api_key.strip():
            return {"success": False, "error": "missing_api_key"}

        post_json = self.request_fn or _default_post_json
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {"submolt": self.submolt, "title": title[:120], "content": content[:1200]}
        try:
            parsed = post_json(f"{self.base_url}/posts", payload, headers, self.timeout_seconds)
            if parsed.get("verification_required"):
                verify_payload = parsed.get("verification", {})
                code = str(verify_payload.get("code", "")).strip()
                challenge = str(verify_payload.get("challenge", "")).strip()
                answer = self._solve_challenge(challenge)
                if code and answer:
                    verify_result = post_json(
                        f"{self.base_url}/verify",
                        {"verification_code": code, "answer": answer},
                        headers,
                        self.timeout_seconds,
                    )
                    parsed["verification_auto_result"] = verify_result
                    if bool(verify_result.get("success")):
                        parsed["verification_required"] = False
            if isinstance(parsed, dict):
                parsed["success"] = True
                return parsed
            return {"success": True}
        except (error.URLError, json.JSONDecodeError) as exc:
            return {"success": False, "error": str(exc)}

    def _solve_challenge(self, challenge: str) -> str:
        words = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20,
            "thirty": 30,
            "forty": 40,
            "fifty": 50,
            "sixty": 60,
            "seventy": 70,
            "eighty": 80,
            "ninety": 90,
        }
        text = re.sub(r"[^a-zA-Z ]", " ", challenge).lower()
        tokens = text.split()
        values: list[int] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in words:
                value = words[token]
                if value >= 20 and i + 1 < len(tokens):
                    next_token = tokens[i + 1]
                    if next_token in words and words[next_token] < 10:
                        value += words[next_token]
                        i += 1
                values.append(value)
            i += 1
        if not values:
            return ""
        if len(values) >= 2:
            top_two = sorted(values, reverse=True)[:2]
            return f"{sum(top_two):.2f}"
        return f"{sum(values):.2f}"
