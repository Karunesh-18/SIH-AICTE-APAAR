from collections import defaultdict
from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import LanguageIn, LoginIn, RefreshIn, UserOut
from app.core import clock
from app.core.config import settings
from app.core.security import decode_token, make_token, verify_password
from app.db.session import get_db, uow
from app.models.user import User
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])

# ponytail: in-memory and per-process; use a shared store if the API is replicated.
_failures: dict[str, list] = defaultdict(list)
_WINDOW = timedelta(minutes=5)


def _bad_login() -> HTTPException:
    return HTTPException(401, "Invalid email or password")


def _recent_failures(email: str) -> list:
    cutoff = clock.now() - _WINDOW
    _failures[email] = [t for t in _failures[email] if t > cutoff]
    return _failures[email]


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if len(_recent_failures(email)) >= settings.login_max_attempts:
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        _failures[email].append(clock.now())
        raise _bad_login()
    _failures.pop(email, None)
    with uow(db):
        audit.append(db, actor_id=user.id, actor_role=user.role, action="AUTH.LOGIN",
                     entity_type="user", entity_id=user.id)
    return {
        "access_token": make_token(user.id, "access"),
        "refresh_token": make_token(user.id, "refresh"),
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    try:
        claims = decode_token(body.refresh_token, "refresh")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token") from None
    user = db.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise HTTPException(401, "Invalid or expired token")
    return {"access_token": make_token(user.id, "access"), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: LanguageIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    with uow(db):
        before = {"language": user.language}
        user.language = body.language
        audit.append(db, actor_id=user.id, actor_role=user.role, action="USER.LANGUAGE",
                     entity_type="user", entity_id=user.id, before=before,
                     after={"language": body.language})
    return user
