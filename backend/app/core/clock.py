"""Single source of 'now'. The demo can move time forward with an offset."""
from datetime import datetime, timedelta, timezone

_offset = timedelta(0)


def now() -> datetime:
    return datetime.now(timezone.utc) + _offset


def set_offset(seconds: float) -> None:
    global _offset
    _offset = timedelta(seconds=seconds)


def get_offset_seconds() -> float:
    return _offset.total_seconds()
