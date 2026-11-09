from sqlalchemy import select

from app.adapters.email import ConsoleEmail
from app.db.session import uow
from app.models.notify import Notification, Outbox
from app.services import notify


class FailingEmail:
    def __init__(self):
        self.calls = 0

    def send(self, to, subject, body):
        self.calls += 1
        raise RuntimeError("smtp down")


def _enqueue(db, user, subject="Hello"):
    return notify.enqueue(db, [user], subject=subject, body="Body", related_type="t",
                          related_id="1")


def test_rolled_back_change_sends_nothing(db, world):
    email = ConsoleEmail()
    try:
        with uow(db):
            _enqueue(db, world["users"]["admin"])
            raise RuntimeError("the business change failed")
    except RuntimeError:
        pass
    notify.dispatch_queued(db, email)
    assert email.sent == []
    assert db.scalars(select(Notification)).all() == []


def test_committed_change_is_emailed_exactly_once(db, world):
    email = ConsoleEmail()
    with uow(db):
        _enqueue(db, world["users"]["admin"])
    notify.dispatch_queued(db, email)
    notify.dispatch_queued(db, email)  # second run must not resend
    assert [m["to"] for m in email.sent] == ["admin@demo.test"]
    statuses = {n.channel: n.status for n in db.scalars(select(Notification))}
    assert statuses == {"IN_APP": "SENT", "EMAIL": "SENT"}
    assert all(o.dispatched_at is not None for o in db.scalars(select(Outbox)))


def test_failed_send_is_retried_then_given_up(db, world):
    email = FailingEmail()
    with uow(db):
        _enqueue(db, world["users"]["admin"])
    for _ in range(5):
        notify.dispatch_queued(db, email)
    assert email.calls == notify.MAX_ATTEMPTS
    mail = db.scalars(select(Notification).where(Notification.channel == "EMAIL")).one()
    assert mail.status == "FAILED"


def test_inbox_is_private_to_each_user(client, login, db, world):
    with uow(db):
        _enqueue(db, world["users"]["admin"], "For admin")
        _enqueue(db, world["users"]["inst_admin"], "For kaveri")
    mine = client.get("/api/v1/notifications", headers=login("admin@demo.test")).json()
    assert [n["subject"] for n in mine] == ["For admin"]
    theirs = client.get("/api/v1/notifications", headers=login("kaveri.admin@demo.test")).json()
    assert [n["subject"] for n in theirs] == ["For kaveri"]


def test_mark_read_and_unread_filter(client, login, db, world):
    with uow(db):
        _enqueue(db, world["users"]["admin"])
    h = login("admin@demo.test")
    nid = client.get("/api/v1/notifications", headers=h).json()[0]["id"]
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=h).status_code == 200
    assert client.get("/api/v1/notifications?unread=true", headers=h).json() == []
    assert len(client.get("/api/v1/notifications", headers=h).json()) == 1


def test_cannot_mark_someone_elses_notification(client, login, db, world):
    with uow(db):
        _enqueue(db, world["users"]["admin"])
    nid = db.scalars(select(Notification.id).where(Notification.channel == "IN_APP")).first()
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=login("kaveri.admin@demo.test"))
    assert r.status_code == 404
