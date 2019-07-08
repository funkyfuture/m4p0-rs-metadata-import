import logging
from pathlib import Path
from typing import Optional

# re-exported constants
DEBUG, INFO = logging.DEBUG, logging.INFO

# re-used global symbol
file_handler: Optional[logging.FileHandler] = None

console_handler = logging.StreamHandler()

log = logging.getLogger("rs-import")
log.setLevel(DEBUG)
log.addHandler(console_handler)


def set_file_log_handler(log_path: Path):
    global file_handler

    if file_handler is not None:
        log.removeHandler(file_handler)

    file_handler = logging.FileHandler(log_path, mode="tw")
    file_handler.setLevel(DEBUG)
    log.addHandler(file_handler)


def set_console_log_level(level: int):
    console_handler.level = level


__all__ = (
    "DEBUG",
    "INFO",
    "log",
    set_file_log_handler.__name__,
    set_console_log_level.__name__,
)
