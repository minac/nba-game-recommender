"""Centralized logging for NBA Game Recommender.

Thin wrapper around structlog. Call setup_logging() once at startup,
then use get_logger(__name__) everywhere.
"""

import structlog

from src.utils.logging_config import setup_logging


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger bound to the given module name."""
    return structlog.get_logger(name)


__all__ = ["get_logger", "setup_logging"]
