"""Phase 5: submission windows, the reminder ladder, R09-R12 and the scheduler switch."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core import clock
from app.domain.ladder import DEFAULT_LADDER
from app.models.audit import AuditLog
from app.models.notify import Notification
from app.models.student import FlagEvent, StudentRecord, Upload
from app.models.windows import SubmissionWindow, WindowAlertLog
from app.services import anomaly, windows
from tests.ingest_helpers import programme, row
from tests.phase5_helpers import add_user, flags_of, old_records, upload

CLOSE = datetime(2026, 9, 30, 12, tzinfo=UTC)


def at(**kw):
    return CLOSE + timedelta(**kw)


@pytest.fixture
def scene(db, world, rules):
    """Kaveri submitted; Malabar (pharmacy, south) and Northfield (north) have not."""
    for inst, name in ((world["kaveri"], "MBA"), (world["malabar"], "B.Pharm"),
                       (world["northfield"], "B.Tech")):
        programme(db, inst, name=name, intake=100)
    upload(db, world["kaveri"], [row(1), row(2)])
    add_user(db, "malabar.admin@demo.test", "INSTITUTION_ADMIN", world["malabar"])
    db.add(SubmissionWindow(cycle_year=2026, opens_at=datetime(2026, 6, 1, tzinfo=UTC),
                            closes_at=CLOSE, ladder=DEFAULT_LADDER))
    db.commit()


def steps_for(db, inst):
    return {s: st for s, st in db.execute(select(WindowAlertLog.step, WindowAlertLog.status).where(
        WindowAlertLog.institution_id == inst.id))}


def reminders(db, email):
    return db.scalars(select(Notification).where(
        Notification.channel == "IN_APP", Notification.related_type == "submission_window",
        Notification.user_id.in_(select_user(email)))).all()


def select_user(email):
    from app.models.user import User
    return select(User.id).where(User.email == email)


def test_nothing_before_the_window_opens(db, scene):
    out = windows.run_cycle(db, datetime(2026, 5, 1, tzinfo=UTC))
    assert out["sent"] == 0 and db.scalar(select(func.count()).select_from(WindowAlertLog)) == 0


def test_reminder_goes_to_non_submitters_only_and_run_is_idempotent(db, world, scene):
    out = windows.run_cycle(db, at(days=-30))
    assert out["sent"] == 2  # Malabar and Northfield
    assert steps_for(db, world["kaveri"]) == {}
    assert steps_for(db, world["malabar"]) == {"T-30d": "SENT"}
    assert len(reminders(db, "malabar.admin@demo.test")) == 1
    again = windows.run_cycle(db, at(days=-30))
    assert again["sent"] == 0 and again["skipped"] == 0
    assert len(reminders(db, "malabar.admin@demo.test")) == 1


def test_clock_jump_sends_latest_and_skips_earlier(db, world, scene):
    out = windows.run_cycle(db, at(days=-6))
    assert steps_for(db, world["malabar"]) == {"T-30d": "SKIPPED", "T-14d": "SKIPPED",
                                                "T-7d": "SENT"}
    assert out["sent"] == 2 and out["skipped"] == 4
    assert len(reminders(db, "malabar.admin@demo.test")) == 1  # one message, not a burst


def test_after_close_late_list_r09_and_officer_message(db, world, scene):
    out = windows.run_cycle(db, at(days=4))
    assert sorted(out["late"]) == ["Malabar Pharmacy College", "Northfield Institute"]
    r09 = flags_of(db, "R09")
    assert sorted(f.institution_id for f in r09) == sorted([world["malabar"].id,
                                                            world["northfield"].id])
    assert all(f.evidence["closed_at"] == "2026-09-30" and f.state == "open" for f in r09)
    assert steps_for(db, world["malabar"])["T+3d"] == "SENT"
    officer = db.scalars(select(Notification).where(
        Notification.user_id.in_(select_user("officer.south@demo.test")),
        Notification.related_type == "submission_window")).all()
    assert officer
    audits = [a.action for a in db.scalars(select(AuditLog))]
    assert "WINDOW.CYCLE_RUN" in audits and audits.count("FLAG.RAISED") >= 2
    windows.run_cycle(db, at(days=4))
    assert len(flags_of(db, "R09")) == 2  # no identical open flag twice


def test_submitting_after_close_stops_further_steps(db, world, scene):
    windows.run_cycle(db, at(days=1))
    upload(db, world["malabar"], [row(40)])
    n = db.scalar(select(func.count()).select_from(WindowAlertLog))
    windows.run_cycle(db, at(days=11))
    assert db.scalar(select(func.count()).select_from(WindowAlertLog)) == n + 2  # Northfield only


def test_institution_type_filter(db, world, scene):
    w = db.scalars(select(SubmissionWindow)).one()
    w.institution_type = "PHARMACY"
    db.commit()
    windows.run_cycle(db, at(days=-30))
    assert steps_for(db, world["northfield"]) == {}
    assert steps_for(db, world["malabar"]) == {"T-30d": "SENT"}


def test_uses_the_demo_clock(db, world, scene):
    offset = clock.get_offset_seconds()
    try:
        clock.set_offset((at(days=-30) - clock.now()).total_seconds())
        windows.run_cycle(db)
        assert steps_for(db, world["malabar"]) == {"T-30d": "SENT"}
    finally:
        clock.set_offset(offset)


# ---- anomaly rules -----------------------------------------------------------------------------

def test_r10_raised_once_with_numbers(db, world, scene):
    old = programme(db, world["kaveri"], name="MBA", intake=100, cycle=2025)
    old_records(db, old, 1)  # 1 last year, 2 now: +100%
    raised = anomaly.run(db, at(days=1), 2026)
    f = [x for x in raised if x.rule_code == "R10"]
    assert len(f) == 1 and f[0].institution_id == world["kaveri"].id
    assert f[0].evidence["previous"] == 1 and f[0].evidence["current"] == 2
    assert "100.0" in f[0].reason and f[0].rule_version_id
    ev = db.scalars(select(FlagEvent).where(FlagEvent.flag_id == f[0].id)).one()
    assert ev.to_state == "raised"
    assert anomaly.run(db, at(days=1), 2026) == []
    assert len(flags_of(db, "R10")) == 1


def test_withdrawn_rows_do_not_count_for_r10(db, world, scene):
    old = programme(db, world["kaveri"], name="MBA", intake=100, cycle=2025)
    old_records(db, old, 1)
    for r in db.scalars(select(StudentRecord).where(StudentRecord.cycle_year == 2026)):
        r.status = "withdrawn"
    db.commit()
    assert anomaly.run(db, at(days=1), 2026) == []


def test_r11_pending_share(db, world, scene):
    upload(db, world["northfield"], [row(60), row(61, apaar_id=""), row(62, apaar_id="")])
    raised = [f for f in anomaly.run(db, at(days=1), 2026) if f.rule_code == "R11"]
    assert len(raised) == 1 and raised[0].evidence["share_pct"] == 66.7


def test_r12_bulk_in_last_hours(db, world, scene):
    rows = [row(100 + n, admission_category="OPEN") for n in range(55)]
    up = upload(db, world["malabar"], rows)
    row_up = db.get(Upload, up.id)
    row_up.created_at = CLOSE - timedelta(hours=2)
    db.commit()
    w = db.scalars(select(SubmissionWindow)).one()
    raised = [f for f in anomaly.run(db, at(days=1), 2026, window=w) if f.rule_code == "R12"]
    assert len(raised) == 1 and raised[0].evidence["top_category"] == "OPEN"
    assert raised[0].evidence["reason"] == "one_category_above_80pct"


def test_run_all_covers_windows_and_is_audited(db, world, scene):
    out = anomaly.run_all(db, at(days=1), actor=None)
    assert any(f.rule_code == "R09" for f in out)


# ---- scheduler switch --------------------------------------------------------------------------

@pytest.mark.parametrize("demo,flag,expected", [
    (True, False, False), (True, True, True), (False, False, True), (False, True, True)])
def test_scheduler_switch(demo, flag, expected):
    from app.services.scheduler import should_run

    assert should_run(demo_mode=demo, scheduler_flag=flag) is expected
