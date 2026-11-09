"""Refresh-token rotation with reuse detection (ADR-026). Callers own the transaction."""
import hashlib
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token, make_token
from app.db.base import new_id
from app.models.system import RefreshToken
from app.models.user import User
from app.services import audit


def _hash(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()


def _now() -> datetime:
    # Real time, like the JWT expiry: the demo clock must not stretch the grace window.
    return datetime.now(UTC)


def issue(db: Session, user_id: str, family_id: str | None = None) -> str:
    family_id = family_id or new_id()
    token = make_token(user_id, "refresh", fam=family_id)
    jti = decode_token(token, "refresh")["jti"]
    db.add(RefreshToken(user_id=user_id, family_id=family_id, jti_hash=_hash(jti)))
    return token


def revoke_family(db: Session, family_id: str) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.family_id == family_id,
                                          RefreshToken.revoked_at.is_(None))
               .values(revoked_at=_now()))


def revoke_user(db: Session, user_id: str) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id,
                                          RefreshToken.revoked_at.is_(None))
               .values(revoked_at=_now()))


def _row(db: Session, raw: str) -> RefreshToken | None:
    try:
        claims = decode_token(raw, "refresh")
    except jwt.PyJWTError:
        return None
    return db.scalars(select(RefreshToken).where(
        RefreshToken.jti_hash == _hash(claims.get("jti", "")))).first()


def rotate(db: Session, raw: str) -> tuple[User, str] | None:
    """New refresh token for a valid one, or None (refused). Reuse revokes the family and
    is audited; that commit happens here so the refusal still persists."""
    row = _row(db, raw)
    if row is None or row.revoked_at is not None:
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    now = _now()
    if row.used_at is not None:
        in_grace = (now - row.used_at <= timedelta(seconds=settings.refresh_grace_seconds)
                    and not row.grace_used)
        if not in_grace:
            revoke_family(db, row.family_id)
            audit.append(db, actor_id=user.id, actor_role=user.role,
                         action="AUTH.REFRESH_REUSED", entity_type="user", entity_id=user.id,
                         after={"family_id": row.family_id})
            db.commit()
            return None
        row.grace_used = True
    else:
        row.used_at = now
    token = issue(db, user.id, row.family_id)
    db.commit()
    return user, token


def logout(db: Session, raw: str) -> None:
    row = _row(db, raw)
    if row is None:
        return
    user = db.get(User, row.user_id)
    revoke_family(db, row.family_id)
    audit.append(db, actor_id=row.user_id, actor_role=user.role if user else None,
                 action="AUTH.LOGOUT", entity_type="user", entity_id=row.user_id)
    db.commit()
