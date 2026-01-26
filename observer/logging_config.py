"""
Logging configuration for Am I Alive? Observer.

Provides structured logging with consistent format.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    name: str = "amialive-observer", level: int = logging.INFO, log_file: Optional[str] = None
) -> logging.Logger:
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

    # Create formatter with structured format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Default logger for Observer
logger = setup_logging("amialive-observer")
