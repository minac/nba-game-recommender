"""
Centralized logging configuration for NBA Game Recommender.

Provides structured logging with INFO, WARNING, and ERROR levels.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.DEBUG,  # Temporarily changed to DEBUG to investigate
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a structured logger with consistent formatting.

    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Logger instance
    """
    return setup_logger(name)


def configure_root_logger(level: int = logging.INFO) -> None:
    """
    Configure the root logger for the entire application.

    Args:
        level: Logging level for the root logger
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
