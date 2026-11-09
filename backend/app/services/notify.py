"""In-app and email notifications through a transactional outbox."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.email import EmailAdapter
from app.core import clock
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


def dispatch_queued(db: Session, email: EmailAdapter) -> None:
    """Run after commit. Safe to run repeatedly: sent rows are skipped, failures retried."""
    pending = db.scalars(
        select(Outbox).where(Outbox.dispatched_at.is_(None), Outbox.attempts < MAX_ATTEMPTS)
        .order_by(Outbox.created_at)
    ).all()
    for item in pending:
        note = db.get(Notification, item.payload["notification_id"])
        user = db.get(User, note.user_id)
        try:
            email.send(user.email, note.subject, note.body)
        except Exception:  # noqa: BLE001  adapters can fail any way; record and retry, never crash
            item.attempts += 1
            if item.attempts >= MAX_ATTEMPTS:
                note.status = "FAILED"
            log.warning("email attempt %s failed for notification %s", item.attempts, note.id)
        else:
            note.status, note.sent_at = "SENT", clock.now()
            item.dispatched_at = clock.now()
        db.commit()
