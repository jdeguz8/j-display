"""Logging configuration helpers for J-Display."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_dir: Path | None = None) -> None:
    """Configure application-wide logging (file + console).

    If log_dir is not provided, a local 'logs' directory is created.
    """
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / "app.log"

    root = logging.getLogger()
    if root.handlers:
        # Already configured (important when running tests / multiple entry points)
        return

    root.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
