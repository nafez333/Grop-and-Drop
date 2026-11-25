"""Application logging configuration.

File output:   data/logs/project_<TIMESTAMP>_<PID>.log
Console output: INFO level to stdout.
Format:        [TIMESTAMP] [LEVEL] [MODULE] message
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Optional

from .constants import LOG_DIR

_CONFIGURED = False
_LOG_FILE: Optional[str] = None


def configure_logging(log_dir: str = str(LOG_DIR), level: int = logging.INFO) -> str:
    """Configure root logging once and return the active log-file path."""
    global _CONFIGURED, _LOG_FILE
    if _CONFIGURED:
        return _LOG_FILE or ""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"project_{timestamp}_{os.getpid()}.log")

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _CONFIGURED = True
    _LOG_FILE = log_file
    logging.getLogger(__name__).info("Logging initialized -> %s", log_file)
    return log_file


def get_logger(name: str) -> logging.Logger:
    """Return a logger for ``name``, configuring logging on first use."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)


# Configure logging the first time the module is imported.
configure_logging()