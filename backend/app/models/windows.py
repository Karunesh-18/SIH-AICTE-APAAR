from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, UTCDateTime
from app.models.enums import check_in


class SubmissionWindow(IdMixin, Base):
    """When institutions must have submitted for a cycle. ladder: [{step, offset_hours, audience}],
    offsets are from closes_at (negative is before). audience is institution, officer or admin."""

    __tablename__ = "submission_window"
    __table_args__ = (CheckConstraint("closes_at > opens_at", name="ck_window_dates"),)
    cycle_year: Mapped[int]
    institution_type: Mapped[str | None] = mapped_column(String(16))  # null: every type
    opens_at: Mapped[datetime] = mapped_column(UTCDateTime)
    closes_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ladder: Mapped[list] = mapped_column(JSON, default=list)


class WindowAlertLog(IdMixin, Base):
    """One row per window, institution and step: the unique key makes a re-run harmless."""

    __tablename__ = "window_alert_log"
    __table_args__ = (
        UniqueConstraint("window_id", "institution_id", "step", name="uq_window_alert"),
        CheckConstraint(check_in("status", ("SENT", "SKIPPED")), name="ck_window_alert_status"),
    )
    window_id: Mapped[str] = mapped_column(ForeignKey("submission_window.id"), index=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"), index=True)
    step: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(8))


class SavedReport(IdMixin, Base):
    __tablename__ = "saved_report"
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    report_key: Mapped[str] = mapped_column(String(48))
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
