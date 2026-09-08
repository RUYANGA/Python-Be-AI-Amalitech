"""Structured JSON log formatter.

Emits one JSON object per line — the shape log-aggregation pipelines
(CloudWatch, Loki, ELK, ...) expect — instead of free-text. Extra fields
passed via ``logger.info(..., extra={...})`` are folded into the record
automatically; the ``key=value`` convention already used throughout this
codebase's log messages still reads fine as plain text inside ``message``.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
}


class JSONFormatter(logging.Formatter):
    """Renders each :class:`logging.LogRecord` as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = {key: value for key, value in record.__dict__.items() if key not in _RESERVED}
        if extra:
            payload["extra"] = extra
        return json.dumps(payload, default=str)
