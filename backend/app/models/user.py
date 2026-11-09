from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin
from app.models.enums import Role, check_in


class User(IdMixin, Base):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(check_in("role", [r.value for r in Role]), name="ck_user_role"),
        CheckConstraint(check_in("language", ("en", "hi")), name="ck_user_language"),
    )
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(24))
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institution.id"))
    language: Mapped[str] = mapped_column(String(2), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserRegion(Base):
    """Which regions an AICTE officer may see."""

    __tablename__ = "user_region"
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("region.id"), primary_key=True)
