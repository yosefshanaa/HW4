"""Structured JSONL logging — boring, file-based, grader-friendly.

Every run writes one JSONL file under the configured log directory so the
notebook and the loop audit can consume run history without parsing free
text. Console output stays human-readable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from hw4.shared.config import Config

LOGGER_ROOT = "hw4"


class JsonlFormatter(logging.Formatter):
    """Render each record as one JSON object per line (machine-readable)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(config: Config, run_id: str, base_dir: Path | str = ".") -> logging.Logger:
    """Configure the hw4 root logger for one run; idempotent per process.

    Handlers are replaced (not appended) so repeated setup in tests does not
    multiply output — a classic logging footgun worth preventing explicitly.
    """
    log_dir = Path(base_dir) / config.logging.get("directory", "results/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_ROOT)
    logger.setLevel(config.logging.get("level", "INFO"))
    logger.handlers.clear()
    file_handler = logging.FileHandler(log_dir / f"{run_id}.jsonl", encoding="utf-8")
    file_handler.setFormatter(JsonlFormatter())
    logger.addHandler(file_handler)
    if config.logging.get("console", True):
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(console)
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Child logger under the hw4 root (inherits run handlers)."""
    return logging.getLogger(f"{LOGGER_ROOT}.{name}")


def log_event(logger: logging.Logger, message: str, **fields: object) -> None:
    """Log with structured fields that land as JSON keys in the run file."""
    logger.info(message, extra={"fields": fields})
