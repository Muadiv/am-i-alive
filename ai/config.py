"""
Configuration management for the AI component.

Provides centralized access to environment variables with defaults and validation.
"""

import os
from typing import Optional

from .logging_config import logger


class Config:
    """Main configuration class for the AI component."""

    # OpenRouter API configuration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_REFERER: str = os.getenv("OPENROUTER_REFERER", "https://am-i-alive.muadiv.com.ar")
    OPENROUTER_TITLE: str = os.getenv("OPENROUTER_TITLE", "Am I Alive - Genesis")

    # Observer communication
    OBSERVER_URL: str = os.getenv("OBSERVER_URL", "http://127.0.0.1")
    AI_COMMAND_PORT: int = int(os.getenv("AI_COMMAND_PORT", "8000"))
    INTERNAL_API_KEY: Optional[str] = os.getenv("INTERNAL_API_KEY")

    # AI behavior
    BOOTSTRAP_MODE: str = os.getenv("BOOTSTRAP_MODE", "basic_facts")
    THINK_INTERVAL_MIN: int = 60
    THINK_INTERVAL_MAX: int = 300
    DEFAULT_THINK_INTERVAL: int = 180

    # Budget configuration
    MONTHLY_BUDGET: float = float(os.getenv("MONTHLY_BUDGET", "5.00"))

    # Weather configuration (Open-Meteo)
    WEATHER_LAT: float = float(os.getenv("WEATHER_LAT", "50.0755"))
    WEATHER_LON: float = float(os.getenv("WEATHER_LON", "14.4378"))

    # X/Twitter integration (deprecated)
    X_API_KEY: Optional[str] = os.getenv("X_API_KEY")
    X_API_SECRET: Optional[str] = os.getenv("X_API_SECRET")
    X_ACCESS_TOKEN: Optional[str] = os.getenv("X_ACCESS_TOKEN")
    X_ACCESS_TOKEN_SECRET: Optional[str] = os.getenv("X_ACCESS_TOKEN_SECRET")

    # Telegram integration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
    TELEGRAM_CHANNEL_ID: Optional[str] = os.getenv("TELEGRAM_CHANNEL_ID")

    # File paths
    CREDITS_FILE: str = os.getenv("CREDITS_FILE", "/app/credits/balance.json")
    MEMORIES_PATH: str = os.getenv("MEMORIES_PATH", "/app/memories")
    MODEL_HISTORY_FILE: str = "/app/workspace/model_history.json"
    IDENTITY_FILE: str = "/app/workspace/identity.json"
    TWITTER_SUSPENSION_FILE: str = "/app/workspace/.twitter_suspended"

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration parameters."""
        errors = []

        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is required")

        if not cls.OBSERVER_URL:
            errors.append("OBSERVER_URL is required")

        if not cls.MONTHLY_BUDGET > 0:
            errors.append("MONTHLY_BUDGET must be greater than 0")

        if errors:
            error_msg = ", ".join(errors)
            logger.error(f"Configuration validation failed: {error_msg}")
            raise RuntimeError(f"Invalid configuration: {error_msg}")

        # Check optional but important parameters
        warnings = []

        if not cls.INTERNAL_API_KEY:
            warnings.append("INTERNAL_API_KEY not set - some Observer calls may fail")

        if not cls.TELEGRAM_BOT_TOKEN:
            warnings.append("TELEGRAM_BOT_TOKEN not set - notifications will fail")

        if warnings:
            for warning in warnings:
                logger.warning(warning)

        logger.info("Configuration validated successfully")


# Initialize and validate configuration
try:
    Config.validate()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.critical(f"Failed to load configuration: {e}")
    raise
