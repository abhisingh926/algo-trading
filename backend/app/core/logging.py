"""Structured logging on top of stdlib `logging`.

stdlib logging is what OpenTelemetry's LoggingHandler / SigNoz hook into, so adding OTel later is
a matter of attaching one more handler in `configure_logging` - call sites do not change.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

_SENSITIVE_KEY = re.compile(r"(token|secret|password|passwd|api[_-]?key|authorization|credential)", re.I)
_REDACTED = "***REDACTED***"
_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


def redact(value: Any, key: str | None = None) -> Any:
    """Recursively mask values whose key looks sensitive."""
    if key is not None and _SENSITIVE_KEY.search(key):
        return _REDACTED
    if isinstance(value, dict):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = redact(value, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras = {
            k: redact(v, k)
            for k, v in record.__dict__.items()
            if k not in _STANDARD_ATTRS and not k.startswith("_")
        }
        suffix = " " + " ".join(f"{k}={v}" for k, v in extras.items()) if extras else ""
        base = f"{datetime.fromtimestamp(record.created):%H:%M:%S} {record.levelname:<7} {record.name}: "
        text = base + record.getMessage() + suffix
        if record.exc_info:
            text += "\n" + self.formatException(record.exc_info)
        return text


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if fmt == "json" else ConsoleFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # httpx logs full URLs at INFO; keep it quiet so query strings never leak.
    for noisy in ("httpx", "httpcore", "aiomysql", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit one structured trading event, e.g. log_event(log, "order_submitted", order_id=...)."""
    logger.log(level, event, extra={k: v for k, v in fields.items() if v is not None})
