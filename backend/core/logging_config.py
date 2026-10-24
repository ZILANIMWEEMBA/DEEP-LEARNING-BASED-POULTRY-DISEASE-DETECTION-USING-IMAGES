"""Structured (JSON-lines) logging with a rotating file handler."""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler

from backend.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_data", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    root = logging.getLogger("poultry")
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    cfg = settings()
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(cfg.log_dir / "app.log", maxBytes=2_000_000, backupCount=3)
    fh.setFormatter(JsonFormatter())
    sh = logging.StreamHandler()
    sh.setFormatter(JsonFormatter())
    root.addHandler(fh)
    root.addHandler(sh)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"poultry.{name}")
