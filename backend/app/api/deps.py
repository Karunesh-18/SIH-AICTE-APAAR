import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "Not authenticated")
    try:
        claims = decode_token(creds.credentials, "access")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token") from None
    user = db.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise HTTPException(401, "Invalid or expired token")
    return user


def require_roles(*roles: Role):
    allowed = {r.value for r in roles}

    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(403, "Not allowed for your role")
        return user

    return dep
