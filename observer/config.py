"""
Configuration management for the Observer component.

Provides centralized access to environment variables with defaults and validation.
"""

import os
from typing import Optional

try:
    from logging_config import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class Config:
    """Main configuration class for the Observer component."""

    # Database configuration
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "/app/data/observer.db")
    MEMORIES_PATH: str = os.getenv("MEMORIES_PATH", "/app/memories")

    # AI communication
    AI_API_URL: str = os.getenv("AI_API_URL", "http://127.0.0.1:8000")
    BUDGET_API_URL: str = os.getenv("BUDGET_API_URL", "http://127.0.0.1:8001")
    INTERNAL_API_KEY: Optional[str] = os.getenv("INTERNAL_API_KEY")

    # Admin and security
    ADMIN_TOKEN: Optional[str] = os.getenv("ADMIN_TOKEN")
    IP_SALT: str = os.getenv("IP_SALT", "default_salt_change_me")
    OBSERVER_ENV: str = os.getenv("OBSERVER_ENV", "development").lower()

    # Local network configuration
    LOCAL_NETWORK_CIDR: str = os.getenv("LOCAL_NETWORK_CIDR", "192.168.0.0/24")

    # Cloudflare proxy IP ranges (used to trust forwarded headers)
    CLOUDFLARE_IP_RANGES = [
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22",
        "2400:cb00::/32",
        "2606:4700::/32",
        "2803:f800::/32",
        "2405:b500::/32",
        "2405:8100::/32",
        "2a06:98c0::/29",
        "2c0f:f248::/32",
    ]

    # Voting system configuration
    VOTING_WINDOW_SECONDS: int = int(os.getenv("VOTING_WINDOW_SECONDS", "3600"))
    MIN_VOTES_FOR_DEATH: int = int(os.getenv("MIN_VOTES_FOR_DEATH", "3"))
    RESPAWN_DELAY_MIN: int = int(os.getenv("RESPAWN_DELAY_MIN", "10"))
    RESPAWN_DELAY_MAX: int = int(os.getenv("RESPAWN_DELAY_MAX", "60"))
    STATE_SYNC_INTERVAL_SECONDS: int = int(os.getenv("STATE_SYNC_INTERVAL_SECONDS", "30"))

    # Token budget configuration
    BUDGET_CHECK_INTERVAL: int = 30
    BUDGET_THRESHOLD: float = 0.01

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration parameters."""
        errors = []

        if not cls.AI_API_URL:
            errors.append("AI_API_URL is required")

        if not cls.VOTING_WINDOW_SECONDS > 0:
            errors.append("VOTING_WINDOW_SECONDS must be greater than 0")

        if not cls.MIN_VOTES_FOR_DEATH > 0:
            errors.append("MIN_VOTES_FOR_DEATH must be greater than 0")

        if errors:
            error_msg = ", ".join(errors)
            logger.error(f"Configuration validation failed: {error_msg}")
            raise RuntimeError(f"Invalid configuration: {error_msg}")

        # Check optional but important parameters
        warnings = []

        if not cls.ADMIN_TOKEN:
            warnings.append("ADMIN_TOKEN not set - God mode will only work from local network")

        if not cls.INTERNAL_API_KEY:
            warnings.append("INTERNAL_API_KEY not set - AI calls may not be authenticated")

        env_ranges = os.getenv("CLOUDFLARE_IP_RANGES")
        if env_ranges:
            ranges = [value.strip() for value in env_ranges.split(",") if value.strip()]
            if ranges:
                cls.CLOUDFLARE_IP_RANGES = ranges

        if cls.IP_SALT == "default_salt_change_me":
            if cls.OBSERVER_ENV in {"production", "prod"}:
                errors.append("IP_SALT must be set for production")
            else:
                warnings.append("IP_SALT not set - using default salt (insecure)")

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
