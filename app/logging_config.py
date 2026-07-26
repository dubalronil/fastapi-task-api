"""Logging setup, configured once at startup.

Two formats. Locally you want to read logs with your eyes, so the default is
plain text. In production a log aggregator has to parse them, so LOG_JSON=true
switches to one JSON object per line.

Every line carries a request id, pulled from a ContextVar rather than being
passed down through every function. The middleware sets it once per request,
and any logger anywhere picks it up automatically.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

from app.config import settings

# "-" is what appears for anything logged outside a request, like startup.
request_id: ContextVar[str] = ContextVar("request_id", default="-")

# Attributes every LogRecord already has. Anything else came from extra={}
# at the call site, and belongs in the output.
_BUILTIN_RECORD_FIELDS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id.get(),
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _BUILTIN_RECORD_FIELDS
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id.get()
        line = super().format(record)
        # Append extra={} fields as key=value, so the access log is readable
        # without hardcoding its fields into the format string.
        extras = " ".join(
            f"{key}={value}"
            for key, value in record.__dict__.items()
            if key not in _BUILTIN_RECORD_FIELDS and key != "request_id"
        )
        return f"{line} {extras}" if extras else line


def configure_logging() -> None:
    if settings.log_json:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = TextFormatter(
            "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    # stdout, not stderr: logs are normal output, and containers and log
    # collectors expect an application to write them there.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Replace whatever is already installed, so calling this twice is safe and
    # our format is the only one in effect.
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Third-party loggers inherit the root level, and several are very chatty
    # at INFO. Raise their floor so our own logs stay findable.
    for noisy in ("httpx", "httpcore", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
