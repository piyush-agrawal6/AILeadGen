import logging
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

console = Console()

LOGS_DIR = Path("logs")
LOG_FILE = LOGS_DIR / "lead-engine.log"

_configured = False


def setup_logging(level: str = "INFO") -> logging.Logger:
    global _configured
    logger = logging.getLogger("leadengine")

    if _configured:
        return logger

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logger.handlers.clear()

    # File handler with detailed formatting
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler using Rich
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )
    rich_handler.setLevel(numeric_level)
    logger.addHandler(rich_handler)

    # Silence overly verbose third-party loggers
    for noisy in ["urllib3", "httpcore", "httpx", "playwright", "duckdb"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
    return logger


def get_logger(name: str = "leadengine") -> logging.Logger:
    if not _configured:
        setup_logging()
    return logging.getLogger(name)
