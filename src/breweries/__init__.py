import logging
from logging import config
from pathlib import Path
import datetime as dt
import json

# Version
__version__ = "1.0.0"

# Redefine JSONFormatter for personalized logging
LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JSONFormatter(logging.Formatter):
    def __init__(self, *args, fmt_keys: dict[str, str] | None = None):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: msg_val
            if (msg_val := always_fields.pop(val, None)) is not None
            else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message


class NonErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= logging.INFO

# Logging configurations
logging_version = 1
disable_existing_loggers = False
logging_dir = Path(__file__).resolve().parents[2].joinpath("logs")
logging_dir.mkdir(parents=True, exist_ok=True)
logging_filename_base = "breweries"
package_name = "breweries"

filters = {
    "no_errors": {
        "()": NonErrorFilter,
    }
}

formatters = {
    "simple":
        {
            "format": "[%(levelname)s|%(module)s|L%(lineno)d] %(name)s: %(message)s | %(asctime)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            "class": "logging.Formatter",
        },
    "custom_formatter":
        {
            "()": JSONFormatter,
            "fmt_keys": {
                "level": "levelname",
                "message": "message",
                "timestamp": "timestamp",
                "logger": "name",
                "module": "module",
                "function": "funcName",
                "line": "lineno",
                "thread_name": "threadName",
            }
        },
}

handlers = {
    "console": {
        "class": "logging.StreamHandler",
        "level": "DEBUG",
        "formatter": "simple",
        "stream": "ext://sys.stdout",
    },
    "info_file_handler": {
        "class": "logging.handlers.RotatingFileHandler",
        "level": "INFO",
        "formatter": "custom_formatter",
        "filters": ["no_errors"],
        "filename": Path.joinpath(logging_dir, f"{logging_filename_base}_info.log.jsonl"),
        "maxBytes": 10485760,
        "backupCount": 20,
        "encoding": "utf8",
    },
    "error_file_handler": {
        "class": "logging.handlers.RotatingFileHandler",
        "level": "ERROR",
        "formatter": "custom_formatter",
        "filename": Path.joinpath(logging_dir, f"{logging_filename_base}_error.log.jsonl"),
        "maxBytes": 10485760,
        "backupCount": 20,
        "encoding": "utf8",
    }
}

loggers = {
    "root": {
        "level": "INFO",
        "handlers": [
            "console",
            "info_file_handler",
            "error_file_handler",
        ],
        "propagate": True,
    }
}

logging_config_dict = {
    "version": logging_version,
    "disable_existing_loggers": disable_existing_loggers,
    "filters": filters,
    "formatters": formatters,
    "handlers": handlers,
    "loggers": loggers,
}

logging.config.dictConfig(logging_config_dict)

# Disable the other module loggers from reporting on anything lower than ERRORS
PACKAGE_LOGGERS = [
    "click",
    "pytest",
    "pyspark",
    "pandas",
    "numexpr.utils",
    "py4j.clientserver",
]

for logger_name in PACKAGE_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.ERROR)
