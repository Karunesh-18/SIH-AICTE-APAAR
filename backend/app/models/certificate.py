from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, UTCDateTime


class CertificateToken(IdMixin, Base):
    """A CERTIFICATE token printed as a QR code. The row exists so the token can be revoked."""

    __tablename__ = "certificate_token"
    record_id: Mapped[str] = mapped_column(ForeignKey("student_record.id"), index=True)
    token_jti: Mapped[str] = mapped_column(String(36), unique=True)
    issued_by: Mapped[str] = mapped_column(ForeignKey("user.id"))
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
