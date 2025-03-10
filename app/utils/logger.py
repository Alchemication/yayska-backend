"""Logging utilities for the application.

This module provides a configured structlog logger for consistent logging across the application.
"""

import logging
import sys

import structlog
from structlog.stdlib import BoundLogger


def configure_logger() -> None:
    """Configure structlog with JSON formatting and other processors.

    This configures structlog with a standard set of processors for consistent
    logging across the application:
    - Context variables merging
    - Log level addition
    - Stack info rendering
    - Exception info
    - ISO timestamp format
    - JSON rendering
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: The name of the logger, typically __name__

    Returns:
        A configured structlog BoundLogger instance
    """
    configure_logger()
    return structlog.get_logger(name)
