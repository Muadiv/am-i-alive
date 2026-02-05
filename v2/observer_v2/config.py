from __future__ import annotations

import os


class Config:
    APP_NAME = os.getenv("V2_APP_NAME", "Am I Alive v2")
    APP_VERSION = os.getenv("V2_APP_VERSION", "0.1.0")
    INTERNAL_API_KEY = os.getenv("V2_INTERNAL_API_KEY", "")
