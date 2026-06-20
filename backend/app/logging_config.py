"""Centralised logging configuration.

Single entry point: ``configure_logging()``. Called from ``app.main`` before
any application code runs.

Format choices
--------------
- ``development`` → plain text with ``extra={}`` fields appended as
  ``key=value`` pairs. Color-friendly via the default ``StreamHandler``.
- ``production``  → single-line JSON-ish records on stdout. Cloudflare, GCP,
  and ``journalctl`` all parse the ``time``/``level``/``logger``/``msg``
  keys out of the box, plus any ``extra={}`` fields.

Level
-----
- Resolved from ``FF_LOG_LEVEL`` (default ``DEBUG`` in development, ``INFO``
  in production/test).
- Third-party loggers (``sqlalchemy.engine``, ``urllib3``) are pinned to
  ``WARNING`` to keep the signal-to-noise ratio sane.
"""

from __future__ import annotations

import json
import logging
import logging.config
import sys
from typing import Any, ClassVar

from app.config import get_settings

# Keys used by Cloud Logging / journalctl / Loki parsers, plus record
# internals and known-noise attributes injected by uvicorn.
_RESERVED_LOGRECORD_ATTRS: ClassVar[frozenset[str]] = frozenset(
    {
        "name",
        "msg",
        "args",
        "message",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "asctime",
        "taskName",
        "color_message",
    }
)


class JsonFormatter(logging.Formatter):
    """Render LogRecords as one-line JSON. Includes any ``extra={}`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


class DevFormatter(logging.Formatter):
    """Plain text formatter that appends ``extra={}`` fields as ``k=v`` pairs."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras: list[str] = []
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            extras.append(f"{key}={value!r}")
        if not extras:
            return base
        return f"{base}  {' '.join(extras)}"


_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging() -> None:
    """Apply the logging configuration.

    Safe to call multiple times; the second invocation re-applies handler
    levels (useful in tests).
    """
    settings = get_settings()

    is_dev = settings.is_development
    level = settings.log_level.upper()

    if is_dev:
        formatter: logging.Formatter = DevFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt=_DATEFMT,
        )
    else:
        formatter = JsonFormatter(datefmt=_DATEFMT)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Route uvicorn through our handler instead of its own.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
        lg.setLevel(level if name != "uvicorn.access" else "INFO")

    # Quiet noisy libraries unless the operator explicitly turns them on.
    logging.getLogger("sqlalchemy.engine").setLevel("WARNING")
    logging.getLogger("urllib3.connectionpool").setLevel("WARNING")
    logging.getLogger("httpx").setLevel("WARNING")

    logging.getLogger("app").info(
        "logging configured",
        extra={"env": settings.app_env, "level": level},
    )
