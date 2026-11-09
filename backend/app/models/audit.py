from datetime import datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime)
    actor_id: Mapped[str | None] = mapped_column(String(64))
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    # UNIQUE: two entries can never claim the same predecessor, so the chain cannot fork.
    prev_hash: Mapped[str] = mapped_column(String(64), unique=True)
    hash: Mapped[str] = mapped_column(String(64))


class AuditCheckpoint(Base):
    """Signed chain head. Anyone holding one can later prove the log was truncated or rewritten."""
    __tablename__ = "audit_checkpoint"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    seq: Mapped[int]  # id of the audit row at the head
    hash: Mapped[str] = mapped_column(String(64))
    count: Mapped[int]
    signed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    token: Mapped[str] = mapped_column(Text)
