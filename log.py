from time import time

from storage import insert_log


def log(level: str, source: str, message: str):
    """Write a log entry to the database and print to stdout."""
    level = level.upper()
    timestamp = int(time())
    print(f"[{level}] [{source}] {message}")
    insert_log(timestamp, level, source, message)
