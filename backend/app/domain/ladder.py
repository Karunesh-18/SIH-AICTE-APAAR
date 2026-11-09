"""Reminder ladder around a submission window's closing time. Pure.

Per audience (institution, officer, admin) only the LATEST due step is sent; earlier due steps
are logged as skipped, so a clock jump never produces a burst of late reminders.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# idea doc section 22. Offsets are hours from closes_at.
DEFAULT_LADDER = [
    {"step": "T-30d", "offset_hours": -720, "audience": "institution"},
    {"step": "T-14d", "offset_hours": -336, "audience": "institution"},
    {"step": "T-7d", "offset_hours": -168, "audience": "institution"},
    {"step": "T0", "offset_hours": 0, "audience": "institution"},
    {"step": "T+3d", "offset_hours": 72, "audience": "officer"},
    {"step": "T+10d", "offset_hours": 240, "audience": "admin"},
]


@dataclass
class Plan:
    fire: list[dict] = field(default_factory=list)
    skip: list[dict] = field(default_factory=list)


def plan(ladder: list[dict], closes_at: datetime, now: datetime, already: set[str]) -> Plan:
    out = Plan()
    for audience in dict.fromkeys(s.get("audience", "institution") for s in ladder):
        due = sorted((s for s in ladder if s.get("audience", "institution") == audience
                      and s["step"] not in already
                      and closes_at + timedelta(hours=s["offset_hours"]) <= now),
                     key=lambda s: s["offset_hours"])
        if due:
            out.fire.append(due[-1])
            out.skip += due[:-1]
    return out
