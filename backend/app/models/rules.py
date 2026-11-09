from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin
from app.models.enums import check_in

RULE_SCOPES = ("upload", "cross", "scheduled")


class Rule(IdMixin, Base):
    __tablename__ = "rule"
    __table_args__ = (CheckConstraint(check_in("scope", RULE_SCOPES), name="ck_rule_scope"),)
    code: Mapped[str] = mapped_column(String(4), unique=True)
    scope: Mapped[str] = mapped_column(String(12))
    title: Mapped[str] = mapped_column(String(120))


class RuleVersion(IdMixin, Base):
    """Every change is a new row. A flag keeps the version it was raised under; revert copies an old row."""

    __tablename__ = "rule_version"
    __table_args__ = (
        UniqueConstraint("rule_code", "version_no", name="uq_rule_version_no"),
        # One active version per rule, enforced by the database (SQLite and Postgres).
        Index("uq_rule_one_active", "rule_code", unique=True,
              sqlite_where=text("is_active"), postgresql_where=text("is_active")),
    )
    rule_code: Mapped[str] = mapped_column(ForeignKey("rule.code"), index=True)
    version_no: Mapped[int]
    enabled: Mapped[bool] = mapped_column(default=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    hard_stop: Mapped[bool] = mapped_column(default=False)
    message_en: Mapped[str] = mapped_column(Text)
    message_hi: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"))
    note: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=False)
