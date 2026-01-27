"""
Logging configuration for Am I Alive? system.

Provides structured logging with consistent format across all components.
"""

import logging
import sys
from typing import Optional


class _SuppressNoisyLogs(logging.Filter):
    """Filter out known noisy log messages from AI services."""

    _NOISY_SUBSTRINGS = (
        "Starting command server on",
        "Force sync request received",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(token in message for token in self._NOISY_SUBSTRINGS)


def setup_logging(name: str = "amialive", level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up structured logging.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional file to write logs to

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Check if logger already has handlers
    if logger.handlers:
        return logger

    noise_filter = _SuppressNoisyLogs()

    # Create formatter with structured format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(noise_filter)
    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(noise_filter)
        logger.addHandler(file_handler)

    return logger


# Default logger for AI
logger = setup_logging("amialive-ai")
