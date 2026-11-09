"""APAAR ID helpers. Pure functions, no framework imports."""
import re

_SEPARATORS = re.compile(r"[\s\- ]+")

_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def normalize(raw: str | None) -> str | None:
    """Strip spaces and hyphens. Blank becomes None. Never rewrites anything else."""
    if raw is None:
        return None
    cleaned = _SEPARATORS.sub("", str(raw))
    return cleaned or None


def verhoeff_ok(digits: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def verhoeff_digit(body: str) -> int:
    c = 0
    for i, ch in enumerate(reversed(body)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return _INV[c]


def check_format(value: str | None, checksum: str = "none", digits: int = 12) -> bool:
    # isascii: str.isdigit() also accepts Devanagari and other scripts' digits.
    if not value or not value.isascii() or not value.isdigit() or len(value) != digits:
        return False
    return verhoeff_ok(value) if checksum == "verhoeff" else True


def mask(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) == 12:
        return f"XXXX XXXX {value[-4:]}"
    return "X" * max(len(value) - 4, 0) + value[-4:] if len(value) > 4 else "X" * len(value)
