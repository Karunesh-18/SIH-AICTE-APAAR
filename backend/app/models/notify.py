from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, UTCDateTime
from app.models.enums import check_in

CHANNELS = ("IN_APP", "EMAIL", "SMS")
STATUSES = ("QUEUED", "SENT", "FAILED", "LOGGED")


class Notification(IdMixin, Base):
    __tablename__ = "notification"
    __table_args__ = (
        CheckConstraint(check_in("channel", CHANNELS), name="ck_notification_channel"),
        CheckConstraint(check_in("status", STATUSES), name="ck_notification_status"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True)
    channel: Mapped[str] = mapped_column(String(8))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(2000))
    related_type: Mapped[str | None] = mapped_column(String(64))
    related_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(8), default="QUEUED")
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Outbox(IdMixin, Base):
    """Written in the same transaction as the change; sent only after that commit."""

    __tablename__ = "outbox"
    kind: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(default=0)
    dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
