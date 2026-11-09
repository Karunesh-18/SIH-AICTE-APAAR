"""seed_demo_windows: a 2026 window, an older cycle for R10, and two institutions that never submit."""
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core import clock
from app.models.org import Institution, Programme
from app.models.student import Upload, ValidationFlag
from app.models.windows import SubmissionWindow
from app.seed import seed, seed_demo_flags, seed_demo_windows
from app.services import anomaly, windows


@pytest.fixture
def demo(db):
    seed(db)
    seed_demo_flags(db)
    seed_demo_windows(db)
    return db


def test_window_previous_cycle_and_non_submitters(demo):
    w = demo.scalars(select(SubmissionWindow)).one()
    assert w.cycle_year == 2026 and w.closes_at > clock.now() > w.opens_at
    assert [s["step"] for s in w.ladder][:2] == ["T-30d", "T-14d"]
    assert demo.scalar(select(func.count()).select_from(Programme).where(
        Programme.cycle_year == 2025)) >= 3
    never = {n for (n,) in demo.execute(select(Institution.name).where(~Institution.id.in_(
        select(Upload.institution_id))))}
    assert never == {"Cauvery Polytechnic", "Yamuna Pharmacy Institute"}


def test_advancing_the_clock_gives_reminders_late_list_and_anomalies(demo):
    w = demo.scalars(select(SubmissionWindow)).one()
    first = windows.run_cycle(demo, clock.now())
    assert first["sent"] == 2 and first["late"] == []
    out = windows.run_cycle(demo, w.closes_at + timedelta(days=4))
    assert sorted(out["late"]) == ["Cauvery Polytechnic", "Yamuna Pharmacy Institute"]
    codes = {f.rule_code for f in demo.scalars(select(ValidationFlag))}
    assert {"R09", "R10"} <= codes
    r10 = demo.scalars(select(ValidationFlag).where(ValidationFlag.rule_code == "R10")).all()
    assert len(r10) == 1 and r10[0].evidence["previous"] == 80
    assert anomaly.run(demo, clock.now(), 2026, w) == []


def test_refuses_to_run_twice(demo):
    with pytest.raises(RuntimeError):
        seed_demo_windows(demo)
