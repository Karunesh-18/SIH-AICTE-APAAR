"""What would make a flag clear, as an i18n key plus values, computed from the flag's evidence.
Pure and advisory: never raises, returns None when the evidence is not usable. No student
identifier is ever returned as a value."""
import math
from numbers import Real

_PLAIN = {"R01", "R03", "R05", "R07", "R08", "R09", "R12"}


def _num(ev: dict, *keys: str) -> dict | None:
    out = {}
    for k in keys:
        v = ev.get(k)
        if isinstance(v, bool) or not isinstance(v, Real):
            return None
        out[k] = v
    return out


def _r11(ev: dict) -> dict | None:
    n = _num(ev, "pending", "total", "limit_pct")
    if n is None:
        return {}  # hint still holds, without the count
    needed = n["pending"] - math.floor(n["total"] * n["limit_pct"] / 100 + 1e-9)
    return {"limit_pct": n["limit_pct"], "needed": max(needed, 1)}


def clear_hint(rule_code: str, evidence: dict) -> tuple[str, dict] | None:
    try:
        if not isinstance(evidence, dict) or not isinstance(rule_code, str):
            return None
        if rule_code in _PLAIN:
            values: dict | None = {}
        elif rule_code == "R02":
            n = _num(evidence, "expected_digits")
            values = n and {"digits": n["expected_digits"]}
        elif rule_code == "R04":
            values = _num(evidence, "count")
        elif rule_code == "R06":
            values = _num(evidence, "allowed", "excess")
        elif rule_code == "R10":
            values = _num(evidence, "rise_pct", "limit_pct")
        elif rule_code == "R11":
            values = _r11(evidence)
        else:
            return None
        return None if values is None else (f"hint.{rule_code}", values)
    except Exception:  # noqa: BLE001  advisory text must never break a response (e.g. inf)
        return None
