"""How officers have treated each rule's flags. Pure: figures only, no judgement."""
from statistics import median

from app.domain.flags import is_terminal


def _days(a, b) -> float:
    return (b - a).total_seconds() / 86400


def summarise(codes, flags, now) -> list[dict]:
    """codes: every rule code (so unflagged rules show zeros). flags: (rule_code, state,
    raised_at, closed_at | None). Flags of unknown codes are ignored."""
    out = []
    for code in codes:
        mine = [f for f in flags if f[0] == code]
        closed = [f for f in mine if is_terminal(f[1])]
        waiting = [f for f in mine if not is_terminal(f[1])]
        n = {s: sum(1 for f in mine if f[1] == s) for s in ("open", "under_review", "resolved",
                                                           "dismissed")}
        # ask_institution is neither open nor closed in the counts; it still ages as unclosed
        n["open"] += sum(1 for f in mine if f[1] == "ask_institution")
        times = [_days(f[2], f[3]) for f in closed if f[3] is not None]
        out.append({
            "code": code, "raised": len(mine), **n,
            "dismissed_share": n["dismissed"] / len(closed) if closed else None,
            "median_days_to_close": median(times) if times else None,
            "oldest_open_days": max((_days(f[2], now) for f in waiting), default=None),
        })
    return out
