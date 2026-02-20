# logger.py

import datetime
import sys
import traceback
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "ERROR"]

# Global minimum level (you can change this to "DEBUG" when you want more noise)
MIN_LEVEL: LogLevel = "INFO"

_LEVEL_ORDER = {
    "DEBUG": 10,
    "INFO": 20,
    "ERROR": 30,
}


def _should_log(level: LogLevel) -> bool:
    return _LEVEL_ORDER[level] >= _LEVEL_ORDER[MIN_LEVEL]


def _log(level: LogLevel, msg: str, exc_info: bool = False) -> None:
    if not _should_log(level):
        return

    # Modern, timezone-aware UTC timestamp
    ts = datetime.datetime.now(datetime.UTC).isoformat()

    stream = sys.stderr if level == "ERROR" else sys.stdout

    # Print the main message
    print(f"[{ts}] [{level}] {msg}", file=stream)

    # If exc_info=True, print full traceback
    if exc_info:
        tb = traceback.format_exc()
        print(tb, file=stream)


def debug(msg: str) -> None:
    _log("DEBUG", msg)


def info(msg: str) -> None:
    _log("INFO", msg)


def error(msg: str, exc_info: bool = False) -> None:
    _log("ERROR", msg, exc_info=exc_info)
