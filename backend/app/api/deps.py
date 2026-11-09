import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db, uow
from app.models.enums import Role
from app.models.org import Institution
from app.models.user import User
from app.services import audit
from app.services.access import can_access_institution

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


def institution_or_403(db: Session, user: User, institution_id: str) -> Institution:
    """404 if it does not exist; 403 (audited) if the user is outside its scope."""
    inst = db.get(Institution, institution_id)
    if inst is None:
        raise HTTPException(404, "Institution not found")
    if not can_access_institution(db, user, inst):
        refuse(db, user, "institution", inst.id)
        raise HTTPException(403, "You do not have access to this institution")
    return inst


def refuse(db: Session, user: User | None, entity_type: str, entity_id: str, **after) -> None:
    with uow(db):
        audit.append(db, actor_id=user.id if user else None,
                     actor_role=user.role if user else "API_KEY", action="ACCESS.REFUSED",
                     entity_type=entity_type, entity_id=entity_id, after=after or None)


def fail(db: Session, user: User | None, err: Exception, entity_type: str, entity_id: str):
    """Map a use-case error to HTTP. A scope failure is audited as a refusal, then 403."""
    from app.services import errors as E

    if isinstance(err, E.Forbidden):
        refuse(db, user, entity_type, entity_id)
        return HTTPException(403, str(err) or "Not allowed")
    code = {E.NotFound: 404, E.Conflict: 409, E.Invalid: 422, E.RateLimited: 429}.get(type(err))
    if code is None:
        raise err
    return HTTPException(code, str(err))
