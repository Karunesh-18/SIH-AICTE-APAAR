"""In-app and email notifications through a transactional outbox."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.email import EmailAdapter, build_email_adapter
from app.core import clock
from app.core.config import settings
from app.models.notify import Notification, Outbox
from app.models.user import User

MAX_ATTEMPTS = 3
log = logging.getLogger(__name__)


def enqueue(db: Session, users: list[User], *, subject: str, body: str,
            related_type: str | None = None, related_id: str | None = None) -> None:
    """Call inside the use case's transaction. Nothing leaves the system until it commits."""
    for u in users:
        common = {"user_id": u.id, "subject": subject, "body": body,
                  "related_type": related_type, "related_id": related_id}
        db.add(Notification(channel="IN_APP", status="SENT", sent_at=clock.now(), **common))
        mail = Notification(channel="EMAIL", status="QUEUED", **common)
        db.add(mail)
        db.flush()
        db.add(Outbox(kind="email", payload={"notification_id": mail.id}))


def dispatch_queued(db: Session, email: EmailAdapter) -> dict:
    """Run after commit. Safe to run repeatedly: sent rows are skipped, failures retried."""
    pending = db.scalars(
        select(Outbox).where(Outbox.dispatched_at.is_(None), Outbox.attempts < MAX_ATTEMPTS)
        .order_by(Outbox.created_at)
    ).all()
    out = {"sent": 0, "failed": 0}
    for item in pending:
        note = db.get(Notification, item.payload["notification_id"])
        user = db.get(User, note.user_id)
        try:
            email.send(user.email, note.subject, note.body)
        except Exception as e:  # noqa: BLE001  adapters can fail any way; record and retry, never crash
            item.attempts += 1
            item.last_error = f"{type(e).__name__}: {e}"[:300]  # adapters keep secrets out
            out["failed"] += 1
            if item.attempts >= MAX_ATTEMPTS:
                note.status = "FAILED"
            log.warning("email attempt %s failed for notification %s", item.attempts, note.id)
        else:
            note.status, note.sent_at = "SENT", clock.now()
            item.dispatched_at, item.last_error = clock.now(), None
            out["sent"] += 1
        db.commit()
    return out


_adapter: EmailAdapter = build_email_adapter(settings)  # EMAIL_BACKEND: console | smtp


def get_adapter() -> EmailAdapter:
    return _adapter


def set_adapter(adapter: EmailAdapter) -> None:
    global _adapter
    _adapter = adapter


def dispatch_now(db: Session) -> dict:
    """Drain the outbox through the configured adapter. Call after a use case commits. Never
    raises: a mail problem must not turn a successful request into an error."""
    try:
        return dispatch_queued(db, _adapter)
    except Exception:
        log.exception("outbox dispatch failed")
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            log.debug("rollback after failed dispatch also failed")
        return {"sent": 0, "failed": 0, "error": True}
