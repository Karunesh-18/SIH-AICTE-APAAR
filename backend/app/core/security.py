from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(settings.bcrypt_rounds)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(user_id: str, kind: str, minutes: float | None = None) -> str:
    # Real time, not the demo clock: JWT libraries verify expiry against the real clock.
    if minutes is None:
        minutes = settings.access_minutes if kind == "access" else settings.refresh_days * 1440
    exp = datetime.now(UTC) + timedelta(minutes=minutes)
    return jwt.encode({"sub": user_id, "typ": kind, "exp": exp}, settings.jwt_secret, ALGORITHM)


def decode_token(token: str, kind: str) -> dict:
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if claims.get("typ") != kind:
        raise jwt.InvalidTokenError("wrong token type")
    return claims
