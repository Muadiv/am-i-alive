from __future__ import annotations

from typing import Optional

import httpx


class HttpClientFactory:
    @staticmethod
    def create(timeout: float = 60.0, headers: Optional[dict[str, str]] = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, headers=headers)
