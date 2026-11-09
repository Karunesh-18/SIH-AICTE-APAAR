from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin
from app.models.enums import check_in

INSTITUTION_TYPES = ("ENGINEERING", "MANAGEMENT", "PHARMACY", "OTHER")
INSTITUTION_STATUS = ("ACTIVE", "UNDER_REVIEW")
LEVELS = ("UG", "PG", "DIPLOMA")


class Region(IdMixin, Base):
    __tablename__ = "region"
    code: Mapped[str] = mapped_column(String(4), unique=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class Institution(IdMixin, Base):
    __tablename__ = "institution"
    __table_args__ = (
        CheckConstraint(check_in("type", INSTITUTION_TYPES), name="ck_institution_type"),
        CheckConstraint(check_in("status", INSTITUTION_STATUS), name="ck_institution_status"),
    )
    aicte_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(16))
    region_id: Mapped[str] = mapped_column(ForeignKey("region.id"))
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    contact_email: Mapped[str | None] = mapped_column(String(200))

    region: Mapped[Region] = relationship(lazy="joined")


class Programme(IdMixin, Base):
    """Intake and supernumerary seats are set by AICTE; institutions only read them."""

    __tablename__ = "programme"
    __table_args__ = (
        CheckConstraint(check_in("level", LEVELS), name="ck_programme_level"),
        CheckConstraint("approved_intake >= 0", name="ck_programme_intake"),
        CheckConstraint("supernumerary_seats >= 0", name="ck_programme_seats"),
    )
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    level: Mapped[str] = mapped_column(String(16))
    cycle_year: Mapped[int]
    duration_years: Mapped[int] = mapped_column(default=2)
    approved_intake: Mapped[int]
    supernumerary_seats: Mapped[int] = mapped_column(default=0)
