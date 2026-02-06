from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib import error, request


@dataclass
class MoltbookPublisher:
    api_key: str
    submolt: str
    base_url: str = "https://www.moltbook.com/api/v1"
    timeout_seconds: int = 20

    def publish(self, title: str, content: str) -> dict[str, Any]:
        if not self.api_key.strip():
            return {"success": False, "error": "missing_api_key"}

        payload = {"submolt": self.submolt, "title": title[:120], "content": content[:1200]}
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/posts",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                parsed["success"] = True
                return parsed
            return {"success": True}
        except (error.URLError, json.JSONDecodeError) as exc:
            return {"success": False, "error": str(exc)}
