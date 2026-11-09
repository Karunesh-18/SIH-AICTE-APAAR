from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, UTCDateTime


class SystemConfig(Base):
    """Small key/value store, e.g. the demo clock offset."""

    __tablename__ = "system_config"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class ApiKey(IdMixin, Base):
    """Per-institution key for machine submission. Only the sha256 of the token is stored."""

    __tablename__ = "api_key"
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    prefix: Mapped[str] = mapped_column(String(12))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scope: Mapped[str] = mapped_column(String(32), default="records:submit")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
