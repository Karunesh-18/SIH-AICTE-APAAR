"""Scheduled rules R09-R12 as pure functions. Advisory: they raise a flag with the numbers used.

All thresholds are placeholders for AICTE to set in the rule parameters.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.rules import FlagDraft


@dataclass(frozen=True)
class UploadFact:
    created_at: datetime
    rows: int
    mix: Mapping[str, int]  # category -> count


def r09_missing(*, submitted: bool, closed: bool, closes_at: datetime,
                params: Mapping) -> FlagDraft | None:
    if submitted or not closed:
        return None
    return FlagDraft("R09", "no_submission", [], {"closed_at": closes_at.date().isoformat()})


def r10_jump(current: int, previous: int | None, params: Mapping) -> FlagDraft | None:
    limit = params.get("jump_pct", 25)
    if not previous:  # no earlier cycle, or an empty one: nothing to compare with
        return None
    pct = round((current - previous) * 100 / previous, 1)
    if pct <= limit:
        return None
    return FlagDraft("R10", "enrolment_jump", [], {"current": current, "previous": previous,
                                                   "rise_pct": pct, "limit_pct": limit})


def r11_pending(pending: int, total: int, params: Mapping) -> FlagDraft | None:
    limit = params.get("pending_pct", 20)
    if not total:
        return None
    pct = round(pending * 100 / total, 1)
    if pct <= limit:
        return None
    return FlagDraft("R11", "pending_share", [], {"pending": pending, "total": total,
                                                  "share_pct": pct, "limit_pct": limit})


def _tvd(a: Mapping[str, int], b: Mapping[str, int]) -> float:
    """Total variation distance between two category mixes, 0 (same) to 1 (disjoint)."""
    ta, tb = sum(a.values()) or 1, sum(b.values()) or 1
    return sum(abs(a.get(k, 0) / ta - b.get(k, 0) / tb) for k in set(a) | set(b)) / 2


def r12_bulk(facts: list[UploadFact], closes_at: datetime, earlier_mix: Mapping[str, int],
             params: Mapping) -> FlagDraft | None:
    """A single upload of >= bulk_rows rows in the last last_hours before close, whose category mix
    is unusual: one category above top_share_pct (80) percent, or a mix that differs from the
    institution's earlier mix by more than mix_dev (0.3). Both limits are placeholders."""
    hours, rows_min = params.get("last_hours", 6), params.get("bulk_rows", 50)
    top_limit, dev_limit = params.get("top_share_pct", 80), params.get("mix_dev", 0.3)
    start = closes_at - timedelta(hours=hours)
    for f in sorted(facts, key=lambda f: f.created_at):
        if not (start <= f.created_at <= closes_at) or f.rows < rows_min or not f.mix:
            continue
        cat, n = max(f.mix.items(), key=lambda kv: kv[1])
        share = round(n * 100 / sum(f.mix.values()), 1)
        base = {"rows": f.rows, "last_hours": hours, "bulk_rows": rows_min,
                "uploaded_at": f.created_at.isoformat(), "top_category": cat,
                "top_share_pct": share}
        if share > top_limit:
            return FlagDraft("R12", "late_bulk_mix", [], base | {"reason": "one_category_above_80pct"})
        dev = round(_tvd(f.mix, earlier_mix), 2) if earlier_mix else 0
        if dev > dev_limit:
            return FlagDraft("R12", "late_bulk_mix", [], base | {
                "reason": "mix_deviates_from_earlier", "deviation": dev, "limit": dev_limit})
    return None
