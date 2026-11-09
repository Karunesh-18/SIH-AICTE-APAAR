"""The outbox is actually drained: after commit in each use case, in the scheduler, and on demand."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import clock
from app.models.notify import Notification, Outbox
from app.models.windows import SubmissionWindow
from app.services import notify, scheduler, windows
from tests.ingest_helpers import csv_bytes, programme, register, row, run


class Recorder:
    def __init__(self):
        self.sent = []

    def send(self, to, subject, body):
        self.sent.append((to, subject))


class Broken:
    def __init__(self):
        self.calls = 0

    def send(self, to, subject, body):
        self.calls += 1
        raise RuntimeError("smtp down")


@pytest.fixture
def mail():
    old = notify.get_adapter()
    rec = Recorder()
    notify.set_adapter(rec)
    yield rec
    notify.set_adapter(old)


@pytest.fixture
def broken():
    old = notify.get_adapter()
    b = Broken()
    notify.set_adapter(b)
    yield b
    notify.set_adapter(old)


def pending(db):
    return db.scalars(select(Outbox).where(Outbox.dispatched_at.is_(None))).all()


def test_upload_processing_sends_the_email(db, world, rules, mail):
    programme(db, world["kaveri"])
    rows = [row(1)]
    register(db, rows)
    run(db, world["kaveri"], csv_bytes(rows))
    assert ("kaveri.admin@demo.test", "Upload processed") in mail.sent
    assert pending(db) == []


def test_flag_action_sends_the_email(client, login, db, world, rules, mail):
    programme(db, world["kaveri"])
    run(db, world["kaveri"], csv_bytes([row(1, apaar_id="")]))
    from app.models.student import ValidationFlag
    f = db.scalars(select(ValidationFlag)).first()
    mail.sent.clear()
    r = client.post(f"/api/v1/flags/{f.id}/review", headers=login("officer.south@demo.test"),
                    json={"note": "on it"})
    assert r.status_code == 200
    assert any(s == "R01 flag is under review" for _, s in mail.sent)
    assert pending(db) == []


def test_run_cycle_sends_reminders(db, world, mail):
    now = clock.now()
    db.add(SubmissionWindow(cycle_year=2026, opens_at=now - timedelta(days=30),
                            closes_at=now + timedelta(days=10),
                            ladder=[{"step": "T-14d", "offset_hours": -336, "audience": "institution"}]))
    db.commit()
    out = windows.run_cycle(db)
    assert out["sent"] > 0
    assert any("reminder" in s.lower() for _, s in mail.sent)
    assert pending(db) == []


def test_verification_notifies_the_institution_by_email(client, login, db, world, mail):
    from tests.phase6_helpers import ask, scene
    scene(db, world)
    r = ask(client, login("verifier@demo.test"), "999900000001")
    assert r.status_code == 200, r.text
    assert any(s.startswith("Student record verified") for _, s in mail.sent)


def test_dispatch_never_raises_even_when_the_adapter_does(db, world, broken):
    from app.db.session import uow
    with uow(db):
        notify.enqueue(db, [world["users"]["admin"]], subject="s", body="b")
    stats = notify.dispatch_now(db)  # must not raise
    assert stats["failed"] == 1 and broken.calls == 1
    assert db.scalars(select(Outbox)).one().attempts == 1


def test_failed_sends_are_retried_then_marked_failed(db, world, broken):
    from app.db.session import uow
    with uow(db):
        notify.enqueue(db, [world["users"]["admin"]], subject="s", body="b")
    for _ in range(notify.MAX_ATTEMPTS + 2):
        notify.dispatch_now(db)
    assert broken.calls == notify.MAX_ATTEMPTS
    mail_row = db.scalars(select(Notification).where(Notification.channel == "EMAIL")).one()
    assert mail_row.status == "FAILED"


def test_a_broken_database_session_does_not_leak_an_exception():
    class Dead:
        def scalars(self, *a, **k):
            raise RuntimeError("db gone")

        def rollback(self):
            pass

    assert notify.dispatch_now(Dead()) == {"sent": 0, "failed": 0, "error": True}


def test_scheduler_tick_dispatches(db, world, mail, monkeypatch):
    from app.db.session import uow
    with uow(db):
        notify.enqueue(db, [world["users"]["admin"]], subject="tick", body="b")
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db)
    scheduler._tick()
    assert ("admin@demo.test", "tick") in mail.sent


def test_admin_endpoint_dispatches_and_is_admin_only(client, login, db, world, mail):
    from app.db.session import uow
    with uow(db):
        notify.enqueue(db, [world["users"]["admin"]], subject="manual", body="b")
    assert client.post("/api/v1/admin/outbox/dispatch",
                       headers=login("officer.south@demo.test")).status_code == 403
    assert client.post("/api/v1/admin/outbox/dispatch").status_code == 401
    r = client.post("/api/v1/admin/outbox/dispatch", headers=login("admin@demo.test"))
    assert r.status_code == 200 and r.json()["sent"] == 1
    assert ("admin@demo.test", "manual") in mail.sent
    assert r.json()["pending"] == 0
