from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, UTCDateTime
from app.models.enums import check_in

PURPOSES = ("EMPLOYMENT", "HIGHER_EDUCATION", "REGULATORY", "SCHOLARSHIP")
# What a verification answer can contain. The policy and the consent each pick from this list.
FIELDS = ("name", "programme", "status", "level", "year_of_study", "admission_category")
VERIFIER_STATUS = ("PENDING", "APPROVED", "REJECTED")
OUTCOMES = ("GRANTED", "REFUSED")
VERIFIER_TYPES = ("EMPLOYER", "INSTITUTION", "REGULATOR", "OTHER")


class Consent(IdMixin, Base):
    __tablename__ = "consent"
    apaar_id: Mapped[str] = mapped_column(String(32), index=True)
    purposes: Mapped[list] = mapped_column(JSON)
    fields: Mapped[list] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(64))
    given_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    withdrawn_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"))


class PurposePolicy(IdMixin, Base):
    """One row per version; the active one has is_active. Older versions stay for the record."""

    __tablename__ = "purpose_policy"
    __table_args__ = (UniqueConstraint("purpose", "version", name="uq_policy_version"),
                      CheckConstraint(check_in("purpose", PURPOSES), name="ck_policy_purpose"))
    purpose: Mapped[str] = mapped_column(String(24), index=True)
    allowed_fields: Mapped[list] = mapped_column(JSON)
    version: Mapped[int]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"))


class Verifier(IdMixin, Base):
    __tablename__ = "verifier"
    __table_args__ = (
        CheckConstraint(check_in("status", VERIFIER_STATUS), name="ck_verifier_status"),
        CheckConstraint(check_in("org_type", VERIFIER_TYPES), name="ck_verifier_type"),
    )
    org_name: Mapped[str] = mapped_column(String(200))
    org_type: Mapped[str] = mapped_column(String(16))
    contact: Mapped[str] = mapped_column(String(200))
    requested_purposes: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(10), default="PENDING", index=True)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"))
    decision_note: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), unique=True)


class VerificationRequest(IdMixin, Base):
    __tablename__ = "verification_request"
    __table_args__ = (CheckConstraint(check_in("outcome", OUTCOMES), name="ck_vreq_outcome"),)
    verifier_id: Mapped[str] = mapped_column(ForeignKey("verifier.id"), index=True)
    apaar_id: Mapped[str] = mapped_column(String(32), index=True)
    purpose: Mapped[str] = mapped_column(String(24))
    fields_requested: Mapped[list] = mapped_column(JSON)
    consent_id: Mapped[str | None] = mapped_column(ForeignKey("consent.id"))
    outcome: Mapped[str] = mapped_column(String(8))
    refusal_reason: Mapped[str | None] = mapped_column(String(32))
    refusal_detail: Mapped[list | None] = mapped_column(JSON)
    token_jti: Mapped[str | None] = mapped_column(String(36), unique=True)
    issued_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
