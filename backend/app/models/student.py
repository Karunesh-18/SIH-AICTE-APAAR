from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core import clock
from app.db.base import Base, IdMixin, UTCDateTime, new_id
from app.models.enums import check_in

RECORD_STATUS = ("submitted", "valid", "flagged", "pending_apaar", "withdrawn")
UPLOAD_SOURCES = ("FILE", "API")
UPLOAD_FORMATS = ("csv", "xlsx", "xls", "json", "api")
UPLOAD_STATUS = ("RECEIVED", "PROCESSING", "DONE", "REJECTED")
FLAG_STATES = ("open", "under_review", "resolved", "dismissed", "ask_institution")


class Upload(IdMixin, Base):
    """A file or API batch. The same file sent twice is two uploads with the same hash."""

    __tablename__ = "upload"
    __table_args__ = (
        CheckConstraint(check_in("source", UPLOAD_SOURCES), name="ck_upload_source"),
        CheckConstraint(check_in("format", UPLOAD_FORMATS), name="ck_upload_format"),
        CheckConstraint(check_in("status", UPLOAD_STATUS), name="ck_upload_status"),
    )
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"), index=True)
    cycle_year: Mapped[int]
    source: Mapped[str] = mapped_column(String(8))
    format: Mapped[str] = mapped_column(String(8))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    row_count: Mapped[int] = mapped_column(default=0)
    accepted_count: Mapped[int] = mapped_column(default=0)
    flagged_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(12), default="RECEIVED")
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"))
    error: Mapped[str | None] = mapped_column(Text)


class StudentRecord(IdMixin, Base):
    """One version of one student's enrolment. Earlier versions stay as rows with is_current false (ADR-012)."""

    __tablename__ = "student_record"
    __table_args__ = (
        CheckConstraint(check_in("status", RECORD_STATUS), name="ck_record_status"),
        CheckConstraint("year_of_study >= 1", name="ck_record_year"),
        CheckConstraint("version >= 1", name="ck_record_version"),
        CheckConstraint("admission_category <> ''", name="ck_record_category"),
        # The database, not the app, refuses a second current record for the same student,
        # programme and cycle. Superseded rows and records still waiting for an ID are exempt.
        Index("uq_record_current", "apaar_id", "programme_id", "cycle_year", unique=True,
              sqlite_where=text("is_current AND apaar_id IS NOT NULL"),
              postgresql_where=text("is_current AND apaar_id IS NOT NULL")),
    )
    # Normalised text (spaces and hyphens removed) as submitted, even when malformed:
    # the checks flag a bad ID, they never rewrite it.
    apaar_id: Mapped[str | None] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(200))
    dob: Mapped[date] = mapped_column(Date)
    programme_id: Mapped[str] = mapped_column(ForeignKey("programme.id"), index=True)
    cycle_year: Mapped[int]
    year_of_study: Mapped[int] = mapped_column(default=1)
    admission_date: Mapped[date] = mapped_column(Date)
    admission_category: Mapped[str] = mapped_column(String(32))
    nri: Mapped[bool] = mapped_column(default=False)
    oci: Mapped[bool] = mapped_column(default=False)
    fn: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16), default="submitted")
    version: Mapped[int] = mapped_column(default=1)
    is_current: Mapped[bool] = mapped_column(default=True)
    superseded_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    superseded_by: Mapped[str | None] = mapped_column(ForeignKey("student_record.id"))
    withdrawn_reason: Mapped[str | None] = mapped_column(Text)
    continues_record_id: Mapped[str | None] = mapped_column(ForeignKey("student_record.id"))
    consent_ref: Mapped[str | None] = mapped_column(String(64))
    consent_source: Mapped[str | None] = mapped_column(String(64))
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("upload.id"), index=True)
    row_number: Mapped[int | None]
    lock_version: Mapped[int] = mapped_column(default=1)

    __mapper_args__ = {"version_id_col": lock_version}  # noqa: RUF012  SQLAlchemy convention


class ValidationFlag(IdMixin, Base):
    __tablename__ = "validation_flag"
    __table_args__ = (CheckConstraint(check_in("state", FLAG_STATES), name="ck_flag_state"),)
    rule_code: Mapped[str] = mapped_column(String(4), index=True)
    rule_version_id: Mapped[str] = mapped_column(ForeignKey("rule_version.id"))
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"), index=True)
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("upload.id"))
    reason_key: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(16), default="open", index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("user.id"))
    lock_version: Mapped[int] = mapped_column(default=1)

    __mapper_args__ = {"version_id_col": lock_version}  # noqa: RUF012  SQLAlchemy convention


class FlagRecord(Base):
    __tablename__ = "flag_record"
    __table_args__ = (PrimaryKeyConstraint("flag_id", "record_id"),)
    flag_id: Mapped[str] = mapped_column(ForeignKey("validation_flag.id"))
    record_id: Mapped[str] = mapped_column(ForeignKey("student_record.id"), index=True)


class FlagEvent(Base):
    __tablename__ = "flag_event"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    flag_id: Mapped[str] = mapped_column(ForeignKey("validation_flag.id"), index=True)
    from_state: Mapped[str | None] = mapped_column(String(16))
    to_state: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("user.id"))
    note: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=clock.now)


class RegistryEntry(IdMixin, Base):
    """Stand-in for the national APAAR registry (MockRegistry reads this table)."""

    __tablename__ = "registry_entry"
    apaar_id: Mapped[str] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    dob: Mapped[date] = mapped_column(Date)
